# OSC RPC

A [remote procedure call](https://en.wikipedia.org/wiki/Remote_procedure_call) library that allows easy integration of Python functionality into SuperCollider by providing [a JSON based protocol](https://en.wikipedia.org/wiki/JSON-RPC) for calling Python functions from within SuperCollider and receiving their results.

## Installation

### Python

Install `osc_rpc` as dependency by executing the following command in a shell

```shell
pip install git+https://github.com/capital-G/osc_rpc.git
```

### SuperCollider

Install it by executing the following commands within SuperCollider

```sclang
// install JSON dependency
Quarks.install("https://github.com/musikinformatik/JSONlib.git");

// install the quark
Quarks.install("https://github.com/capital-G/osc_rpc.git");

// restart the interpreter so the new classes are available
thisProcess.recompile;
```

## Quickstart

Lets init a RPC server in Python via

```python
from osc_rpc import OSCRPCServer

server = OSCRPCServer()
```

Adding for example a function `add` to the server can be done via

```python
def add(x, y):
    return x+y

server.register_function(add)
```

To start accepting requests it is necessary to start the server via

```python
server.serve_forever()
```

After the server has started it is time to setup the client within SuperCollider so it is possible to call the Python functions from within SuperCollider.

```supercollider
x = OSCRPCClient();

// print all available functions
x.getMethods;
// add(x, y)

// call `add` function
z = x.add(4, 5);
// z is a OSCRPCResponse object which is acts as a wrapper for
// an async result as it is not possible within sclang to wait

z.result;
// -> 9

// it is also possible to pass a callback as a last argument to the
// invokation. The callback will be called as soon as the result has
// been received and will receive the result as a first argument

x.add(4, 5, {|r| "The result is %".format(r).postln});
// "The result is 9"
```

The data-serialization between both languages is handled by JSON, so only basic data types can be transferred.

## License

AGPL-3.0
