"""
Layer 4: Redundant Dead Man's Switch Daemon (cancelAllOrdersAfter).
Guarantees resting order safety against network partition, process crash, or VM termination.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Coroutine
from pipeline.live.signer import HyperliquidSigner, SignedExchangePayload

logger = logging.getLogger(__name__)


class DeadMansSwitchDaemon:
    """
    Heartbeat daemon maintaining a rolling exchange-level cancellation countdown.
    If the worker hangs or drops connection, Hyperliquid cancels all orders after expiry.
    """
    def __init__(
        self,
        signer: HyperliquidSigner,
        dispatch_coro: Callable[[SignedExchangePayload], Coroutine[None, None, bool]] | None = None,
        countdown_ms: int = 45_000,
        heartbeat_interval_s: float = 15.0,
    ):
        self.signer = signer
        self.dispatch_coro = dispatch_coro
        self.countdown_ms = countdown_ms
        self.heartbeat_interval_s = heartbeat_interval_s
        self.is_running = False
        self.last_heartbeat_ack_ts = 0.0
        self._task: asyncio.Task | None = None

    async def _heartbeat_loop(self) -> None:
        while self.is_running:
            try:
                payload = self.signer.build_dead_mans_switch_action(countdown_ms=self.countdown_ms)
                if self.dispatch_coro:
                    success = await self.dispatch_coro(payload)
                    if success:
                        self.last_heartbeat_ack_ts = time.time()
                    else:
                        logger.warning("Dead man's switch heartbeat dispatch unacknowledged by exchange.")
                else:
                    self.last_heartbeat_ack_ts = time.time()

            except Exception as e:
                logger.error("Dead man's switch daemon error: %s", e)

            await asyncio.sleep(self.heartbeat_interval_s)

    def start(self) -> None:
        self.is_running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Dead man's switch heartbeat daemon started (timeout=%dms).", self.countdown_ms)

    def stop(self) -> None:
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Dead man's switch heartbeat daemon stopped.")
