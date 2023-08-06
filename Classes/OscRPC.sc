OSCRPCResponse {
	var <uuid;
	var <method;
	var <args;
	var <callback;

	var <>ready;
	var <response;
	var <>fault;

	*new {|uuid, method, args, callback|
		^this.newCopyArgs(uuid, method, args, callback).init;
	}

	init {
		ready = false;
	}

	response_ {|newResponse|
		response = newResponse;
		if(callback.notNil.and(fault.isNil), {
			callback.value(newResponse);
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
			var isNull = payload.response.value.isNil;

			if(payload.fault.value.notNil, {
				"RPC failed: %".format(payload.fault).postln;
			});
			responses[payload.uuid].fault = payload.fault.value;
			responses[payload.uuid].response = if(isNull, {nil}, {payload.response});
			responses[payload.uuid].ready = true;
		}, path: "/rpc/_reply");
	}

	getMethods {
		this.perform("_methods".asSymbol, args: [{|m| m.do({|f| f.postln})}]);
	}

    doesNotUnderstand { | selector ...args |
		var uuid = UniqueID.next;
		var response;
		var callback = {};
		var payload;

		if(args.last.isFunction, {
			callback = args.last;
			args.remove(callback);
		});

		payload = (
			arguments: args,
			uuid: uuid,
		);
		NetAddr(hostname, port).sendMsg(
			"/rpc/%".format(selector),
			JSONlib.convertToJSON(payload)
		);
		response = OSCRPCResponse(uuid, selector, args, callback);
		responses[uuid] = response;

		// check for timeout
		Task({
			timeout.wait;
			if(responses[uuid].ready.not, {
				"RPC '%(%)' timed out".format(selector, args.join(", ")).postln;
				responses[uuid].ready = true;
				responses[uuid].fault = "timeout";
			});
		}).start;
		^response;
    }
}
