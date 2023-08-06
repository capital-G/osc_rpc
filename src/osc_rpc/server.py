import inspect
import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, overload

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ForkingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

logger = logging.getLogger(__name__)


@dataclass
class RPCRequest:
    uuid: int
    address: str
    arguments: List[str] = field(default_factory=list)


@dataclass
class RPCResponse:
    uuid: int
    response: Any
    fault: Optional[str] = None


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
            message = RPCRequest(address=osc_address, **json.loads(osc_args[0]))
        except TypeError:
            logger.error(f"Received malformed OSC content: {osc_args}")
            return

        if osc_address == "/rpc/_methods":
            return self._send_reply(
                reply_address,
                message=RPCResponse(uuid=message.uuid, response=self._list_methods()),
            )

        if (rpc_method := osc_address.replace("/rpc/", "")) in self._call_map.keys():
            try:
                return self._send_reply(
                    reply_address,
                    message=RPCResponse(
                        uuid=message.uuid,
                        response=self._call_map.get(rpc_method)(*message.arguments),
                    ),
                )
            except Exception as e:
                return self._send_reply(
                    reply_address,
                    message=RPCResponse(
                        uuid=message.uuid,
                        response=None,
                        fault=str(e),
                    ),
                )
        else:
            error_message = f"Received unknown procedure '{rpc_method}' with args {message.arguments}"
            logger.error(error_message)
            return self._send_reply(
                reply_address,
                message=RPCResponse(
                    uuid=message.uuid,
                    response=None,
                    fault=error_message,
                ),
            )

    def _send_reply(self, reply_address: Tuple[str, int], message: RPCResponse) -> None:
        payload = json.dumps(asdict(message))
        SimpleUDPClient(*reply_address).send_message(
            address="/rpc/_reply", value=payload
        )

    def _list_methods(self) -> List[str]:
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

    server = OSCRPCServer()
    server.register_function(add)
    server.register_function(div)
    try:
        transport, protocol = server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server")
