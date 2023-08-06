OSCRPCResult {
	var <id;
	var <method;
	var <params;
	var <callback;

	var <>ready;
	var <result;
	var <>error;

	*new {|uuid, method, args, callback|
		^this.newCopyArgs(uuid, method, args, callback).init;
	}

	init {
		ready = false;
	}

	result_ {|newResult|
		result = newResult;
		if(callback.notNil.and(error.isNil), {
			callback.value(newResult);
		});
	}
}

OSCRPCClient {
	var <hostname;
	var <port;
	var <>timeout;

	var <responder;
	var <responses;

	*new {|hostname="127.0.0.1", port=8000, timeout=60|
		^super.newCopyArgs(hostname, port, timeout).init;
	}

	init {
		responses = ();
		responder = OSCFunc({|m|
			var payload = JSONlib.convertToSC(m[1]);
			var isNull = payload.result.value.isNil;

			if(payload.error.value.notNil, {
				"RPC % failed: %".format(payload.id, payload.error).postln;
			});
			responses[payload.id].error = payload.error.value;
			responses[payload.id].result = if(isNull, {nil}, {payload.result});
			responses[payload.id].ready = true;
		}, path: "/rpc/_reply");
	}

	getMethods {
		this.perform("_get_methods".asSymbol, args: [{|m| m.do({|f| f.postln})}]);
	}

    doesNotUnderstand { | selector ...args |
		var id = UniqueID.next;
		var response;
		var callback = {};
		var payload;

		if(args.last.isFunction, {
			callback = args.last;
			args.remove(callback);
		});

		payload = (
			params: args,
			id: id,
			method: selector,
		);
		NetAddr(hostname, port).sendMsg(
			"/rpc/%".format(selector),
			JSONlib.convertToJSON(payload)
		);
		response = OSCRPCResult(id, "/rpc/call", args, callback);
		responses[id] = response;

		// check for timeout
		Task({
			timeout.wait;
			if(responses[id].ready.not, {
				"RPC % '%(%)' timed out".format(id, selector, args.join(", ")).postln;
				responses[id].ready = true;
				responses[id].fault = "timeout";
			});
		}).start;
		^response;
    }
}
