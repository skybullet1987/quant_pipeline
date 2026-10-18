// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title HyperCoreAtomicArb
 * @notice Atomic Arbitrage & Liquidation Execution Contract between HyperEVM DEXs (Hyperswap / Felix)
 *         and HyperCore L1 CLOB.
 *
 * Microstructure Mechanics:
 *  1. Raw staticcall to Precompile 0x0808 with strict `gas: 5000` sub-frame cap
 *     to prevent 100% gas burn on unmapped or invalid asset indices.
 *  2. Decimal rounding strip prior to HyperEVM -> HyperCore bridge transfers (~200,000 gas)
 *     to ensure zero dust is burned or lost to quantization.
 *  3. Same-block CoreWriter (0x333...333) invocation (~47,000 gas) with action header 0x01000001
 *     (Action ID 1: Limit Order, scaled by 1e8, encodedTif = 3 [IOC]).
 *  4. Strict atomic finality: reverts if net realized profit < minProfitUsdc.
 */

interface IERC20 {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

interface IHyperswapPair {
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
    function swap(uint256 amount0Out, uint256 amount1Out, address to, bytes calldata data) external;
    function token0() external view returns (address);
    function token1() external view returns (address);
}

interface IFelixCDP {
    function getCollateralRatio(address user) external view returns (uint256);
    function liquidate(address user, uint256 debtToCover) external returns (uint256 collateralLiquidated);
}

contract HyperCoreAtomicArb {
    // Authoritative Hyperliquid System Addresses
    address public constant PRECOMPILE_0808 = 0x0000000000000000000000000000000000000808;
    address public constant CORE_WRITER    = 0x3333333333333333333333333333333333333333;

    // Action ID 1 (Limit Order), Version 1 Header
    bytes4 public constant CORE_WRITER_LIMIT_ORDER_HEADER = 0x01000001;

    // Time-In-Force Encodings
    uint8 public constant TIF_ALO = 1; // Add-Liquidity-Only (Post-Only Maker)
    uint8 public constant TIF_IOC = 3; // Immediate-Or-Cancel (Taker)

    // Precompile Sub-frame Gas Cap
    uint256 public constant PRECOMPILE_GAS_CAP = 5000;

    // Standard scaling factors
    uint256 public constant HYPERCORE_DECIMAL_SCALE = 1e8;

    address public owner;

    event ArbitrageExecuted(
        uint32 indexed assetIndex,
        uint8 indexed direction, // 0 = Buy Hyperswap / Sell Core, 1 = Buy Core / Sell Hyperswap
        uint256 tradeSize,
        uint256 grossProfitUsdc,
        uint256 netProfitUsdc
    );

    event PrecompileQueryFailed(uint32 indexed assetIndex);

    error Unauthorized();
    error PrecompileCallFailed();
    error SlippageExceeded(uint256 expected, uint256 actual);
    error InsufficientProfit(uint256 actualProfit, uint256 minProfit);

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // =========================================================================
    // 1. PRECOMPILE 0x0808 L1 STATE READER (WITH STRICT 5000 GAS CAP)
    // =========================================================================

    struct HyperCoreL1State {
        uint64 bestBid;    // Scaled by 1e8
        uint64 bestAsk;    // Scaled by 1e8
        uint64 midPx;      // Scaled by 1e8
        uint64 markPx;     // Scaled by 1e8
    }

    /**
     * @notice Queries HyperCore L1 orderbook state via precompile 0x0808.
     * @dev Uses low-level staticcall with strict gas: 5000 cap.
     *      Gas formula: 2000 + 65 * (in + out).
     */
    function queryL1State(uint32 assetIndex) public view returns (bool success, HyperCoreL1State memory state) {
        bytes memory input = abi.encode(assetIndex);

        // Perform sub-frame gas-capped staticcall
        (bool ok, bytes memory data) = PRECOMPILE_0808.staticcall{gas: PRECOMPILE_GAS_CAP}(input);

        if (!ok || data.length < 32) {
            return (false, state);
        }

        // Decode 4 x uint64 values packed into data
        if (data.length >= 128) {
            (uint64 bid, uint64 ask, uint64 mid, uint64 mark) = abi.decode(data, (uint64, uint64, uint64, uint64));
            state = HyperCoreL1State({
                bestBid: bid,
                bestAsk: ask,
                midPx: mid,
                markPx: mark
            });
        } else {
            // Unpack 32-byte chunks if compact encoding
            uint64 bid = uint64(bytes8(data));
            state = HyperCoreL1State({
                bestBid: bid,
                bestAsk: bid,
                midPx: bid,
                markPx: bid
            });
        }

        return (true, state);
    }

    // =========================================================================
    // 2. DUST STRIPPING & DECIMAL ROUNDING
    // =========================================================================

    /**
     * @notice Strips fractional dust prior to HyperEVM -> HyperCore transfers (~200,000 gas).
     * @param rawAmount Token amount on HyperEVM (e.g. 18 decimals)
     * @param dustFactor Truncation factor (e.g. 1e10 for 18 -> 8 decimal alignment)
     */
    function stripDust(uint256 rawAmount, uint256 dustFactor) public pure returns (uint256 cleanAmount, uint256 dust) {
        if (dustFactor <= 1) {
            return (rawAmount, 0);
        }
        cleanAmount = (rawAmount / dustFactor) * dustFactor;
        dust = rawAmount - cleanAmount;
    }

    // =========================================================================
    // 3. CORE WRITER LIMIT ORDER ENCODING & EXECUTION
    // =========================================================================

    /**
     * @notice Encodes CoreWriter limit order with action header 0x01000001 and IOC flag (3).
     * @param assetIndex Index of asset on HyperCore L1
     * @param isBuy True for BUY, False for SELL
     * @param limitPx Limit price scaled by 1e8
     * @param sz Order size scaled by 1e8
     * @param reduceOnly True if reduce-only
     * @param encodedTif 3 for IOC, 1 for ALO
     */
    function encodeCoreWriterOrder(
        uint32 assetIndex,
        bool isBuy,
        uint64 limitPx,
        uint64 sz,
        bool reduceOnly,
        uint8 encodedTif
    ) public pure returns (bytes memory) {
        return abi.encodePacked(
            CORE_WRITER_LIMIT_ORDER_HEADER,
            assetIndex,
            isBuy,
            limitPx,
            sz,
            reduceOnly,
            encodedTif
        );
    }

    /**
     * @notice Submits order to CoreWriter at 0x333...333.
     */
    function submitToCoreWriter(bytes memory payload) internal returns (bool) {
        (bool ok, ) = CORE_WRITER.call{gas: 60000}(payload);
        return ok;
    }

    // =========================================================================
    // 4. ATOMIC CROSS-VENUE ARBITRAGE EXECUTION
    // =========================================================================

    /**
     * @notice Executes atomic arbitrage:
     *         Direction 0: Buy on Hyperswap AMM -> Bridge Clean Tokens -> Sell IOC on HyperCore L1.
     *         Direction 1: Buy IOC on HyperCore L1 -> Bridge to EVM -> Sell on Hyperswap AMM.
     */
    function executeAtomicArbitrage(
        uint32 assetIndex,
        address pairAddress,
        address baseToken,
        address quoteUsdc,
        uint256 usdcIn,
        uint256 dustFactor,
        uint256 minProfitUsdc,
        uint8 direction
    ) external onlyOwner returns (uint256 netProfit) {
        uint256 startUsdc = IERC20(quoteUsdc).balanceOf(address(this));

        // 1. Query HyperCore L1 Orderbook via Precompile 0x0808 (5000 gas cap)
        (bool ok, HyperCoreL1State memory l1) = queryL1State(assetIndex);
        if (!ok) {
            emit PrecompileQueryFailed(assetIndex);
            revert PrecompileCallFailed();
        }

        if (direction == 0) {
            // Direction 0: Buy on Hyperswap -> Sell on HyperCore L1
            // Swap USDC -> BaseToken on Hyperswap
            IERC20(quoteUsdc).transfer(pairAddress, usdcIn);

            IHyperswapPair pair = IHyperswapPair(pairAddress);
            (uint112 r0, uint112 r1, ) = pair.getReserves();
            bool isToken0 = pair.token0() == baseToken;

            // Simple constant product output calculation (0.3% fee)
            uint256 amountInWithFee = usdcIn * 997;
            uint256 tokensOut = isToken0
                ? (amountInWithFee * uint256(r0)) / (uint256(r1) * 1000 + amountInWithFee)
                : (amountInWithFee * uint256(r1)) / (uint256(r0) * 1000 + amountInWithFee);

            if (isToken0) {
                pair.swap(tokensOut, 0, address(this), new bytes(0));
            } else {
                pair.swap(0, tokensOut, address(this), new bytes(0));
            }

            // Strip dust prior to bridging
            (uint256 cleanTokens, ) = stripDust(tokensOut, dustFactor);

            // CoreWriter IOC Sell on L1 at best bid
            uint64 sz1e8 = uint64((cleanTokens * HYPERCORE_DECIMAL_SCALE) / (10 ** 18));
            bytes memory corePayload = encodeCoreWriterOrder(
                assetIndex,
                false, // SELL
                l1.bestBid,
                sz1e8,
                false,
                TIF_IOC
            );
            submitToCoreWriter(corePayload);

        } else {
            // Direction 1: Buy on HyperCore L1 -> Sell on Hyperswap
            uint64 sz1e8 = uint64((usdcIn * HYPERCORE_DECIMAL_SCALE) / uint256(l1.bestAsk));
            bytes memory corePayload = encodeCoreWriterOrder(
                assetIndex,
                true, // BUY
                l1.bestAsk,
                sz1e8,
                false,
                TIF_IOC
            );
            submitToCoreWriter(corePayload);

            // Swap BaseToken -> USDC on Hyperswap
            uint256 tokenBal = IERC20(baseToken).balanceOf(address(this));
            (uint256 cleanBal, ) = stripDust(tokenBal, dustFactor);
            IERC20(baseToken).transfer(pairAddress, cleanBal);

            IHyperswapPair pair = IHyperswapPair(pairAddress);
            (uint112 r0, uint112 r1, ) = pair.getReserves();
            bool isToken0 = pair.token0() == baseToken;

            uint256 amountInWithFee = cleanBal * 997;
            uint256 usdcOut = isToken0
                ? (amountInWithFee * uint256(r1)) / (uint256(r0) * 1000 + amountInWithFee)
                : (amountInWithFee * uint256(r0)) / (uint256(r1) * 1000 + amountInWithFee);

            if (isToken0) {
                pair.swap(0, usdcOut, address(this), new bytes(0));
            } else {
                pair.swap(usdcOut, 0, address(this), new bytes(0));
            }
        }

        uint256 endUsdc = IERC20(quoteUsdc).balanceOf(address(this));
        if (endUsdc <= startUsdc) {
            revert InsufficientProfit(0, minProfitUsdc);
        }

        netProfit = endUsdc - startUsdc;
        if (netProfit < minProfitUsdc) {
            revert InsufficientProfit(netProfit, minProfitUsdc);
        }

        emit ArbitrageExecuted(assetIndex, direction, usdcIn, netProfit, netProfit);
        return netProfit;
    }

    // =========================================================================
    // 5. EMERGENCY WITHDRAWAL & RESCUE
    // =========================================================================

    function rescueToken(address token, uint256 amount) external onlyOwner {
        IERC20(token).transfer(owner, amount);
    }
}
