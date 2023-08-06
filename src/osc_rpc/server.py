import inspect
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, overload

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ForkingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

logger = logging.getLogger(__name__)


@dataclass
class RPCRequest:
    method: str
    id: Optional[int]
    params: Optional[List[str]] = None
    jsonrpc: str = "2.0"


@dataclass
class RPCResponse:
    id: int
    result: Optional[Any]
    error: Optional[str] = None
    jsonrpc: str = "2.0"


class OSCRPCServer(Dispatcher, ForkingOSCUDPServer):
    def __init__(self, server_address: Optional[Tuple[str, int]] = None) -> None:
        server_address = server_address if server_address else ("127.0.0.1", 8000)
        ForkingOSCUDPServer.__init__(
            self,
            server_address=server_address,
            dispatcher=self,
        )
        Dispatcher.__init__(self)
        self.set_default_handler(self._handle_call, needs_reply_address=True)
        self._call_map: Dict[str, Callable] = {}

    @staticmethod
    def _get_func_name(function: Callable, name: Optional[str] = None) -> str:
        return name if name else function.__name__

    def register_function(self, function: Callable, name: Optional[str] = None):
        # do not use map directly b/c we want to extract the reply address
        # and wrap and respond to the call respectively
        self._call_map[self._get_func_name(function, name)] = function

    @overload
    def unregister_function(self, function: Callable):
        ...

    @overload
    def unregister_function(self, name: str):
        ...

    def unregister_function(
        self, function: Optional[Callable] = None, name: Optional[str] = None
    ):
        del self._call_map[self._get_func_name(function, name)]

    def _handle_call(
        self, reply_address: Tuple[str, int], osc_address: str, *osc_args
    ) -> None:
        try:
            message = RPCRequest(**json.loads(osc_args[0]))
        except TypeError as e:
            logger.error(f"Received malformed OSC content: {osc_args} - error: {e}")
            return

        if message.method == "_get_methods":
            return self._send_reply(
                reply_address,
                message=RPCResponse(id=message.id, result=self._get_methods()),
            )

        logger.debug(f"Received message {message}")

        if message.method in self._call_map.keys():
            try:
                logger.info(f"Call '{message.method}' with params {message.params}")
                return self._send_reply(
                    reply_address,
                    message=RPCResponse(
                        id=message.id,
                        result=self._call_map.get(message.method)(*message.params),
                    ),
                )
            except Exception as e:
                logger.info(
                    f"Failed to call '{message.method}' with params {message.params} - {e}"
                )
                return self._send_reply(
                    reply_address,
                    message=RPCResponse(
                        id=message.id,
                        result=None,
                        error=str(e),
                    ),
                )
        else:
            error_message = f"Received unknown procedure '{message.method}' with args {message.params}"
            logger.error(error_message)
            return self._send_reply(
                reply_address,
                message=RPCResponse(
                    id=message.id,
                    result=None,
                    error=error_message,
                ),
            )

    def _send_reply(self, reply_address: Tuple[str, int], message: RPCResponse) -> None:
        payload = json.dumps(asdict(message))
        SimpleUDPClient(*reply_address).send_message(
            address="/rpc/_reply", value=payload
        )

    def _get_methods(self) -> List[str]:
        l: List[str] = []
        for name, f in self._call_map.items():
            l.append(f"{name}{inspect.signature(f)}")
        return l

    def serve_forever(self, poll_interval: float = 0.5) -> None:
        print(f"Start serving on {self.server_address[0]}:{self.server_address[1]}")
        return super().serve_forever(poll_interval)


if __name__ == "__main__":

    def add(x, y):
        return x + y

    def div(x: float, y: float) -> float:
        return x / y

    logger.setLevel(logging.INFO)

    server = OSCRPCServer()
    server.register_function(add)
    server.register_function(div)

    try:
        transport, protocol = server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server")
