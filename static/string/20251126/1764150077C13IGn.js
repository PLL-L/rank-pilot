// 异步函数处理工具
var w = (n, r, e) => new Promise((o, x) => {
    var t = a => {
        try {
            u(e.next(a))
        } catch (d) {
            x(d)
        }
    }, c = a => {
        try {
            u(e.throw(a))
        } catch (d) {
            x(d)
        }
    }, u = a => a.done ? o(a.value) : Promise.resolve(a.value).then(t, c);
    u((e = e.apply(n, r)).next())
});

// 导入 b >>> ipv4  e >>> ipv6  的正则
import {b as g, e as I} from "./DyTbmUAG.js";

// Sentry 调试 ID 初始化
try {
    let n = typeof window != "undefined" ? window : typeof global != "undefined" ? global : typeof globalThis != "undefined" ? globalThis : typeof self != "undefined" ? self : {},
        r = new n.Error().stack;
    r && (n._sentryDebugIds = n._sentryDebugIds || {}, n._sentryDebugIds[r] = "5e6c5966-4b1e-4cb5-9af6-7c3446a63239", n._sentryDebugIdIdentifier = "sentry-dbid-5e6c5966-4b1e-4cb5-9af6-7c3446a63239")
} catch (n) {
}

// 当前基准为 f  num - 292;
(function (n, r) {
    const e = f, o = n();
    for (; ;) try {
        if (parseInt(e(323)) / 1 + parseInt(e(295)) / 2 + -parseInt(e(330)) / 3 * (-parseInt(e(340)) / 4) + parseInt(e(319)) / 5 + -parseInt(e(326)) / 6 + parseInt(e(335)) / 7 + parseInt(e(321)) / 8 * (-parseInt(e(309)) / 9) === r) break;
        o.push(o.shift())
    } catch (x) {
        o.push(o.shift())
    }
})(h, 670153);

function h() {
    const n = ["iption", "parse", "onicecandi", "x.net?tran", "eerConnect", "nection", "length", "1036432VoeLhR", "localDescr", "prototype", "sdp", "ion", "log", 'ctor("retu', "date", "complete", "RTCPeerCon", "iceGatheri", "push", "__proto__", "setLocalDe", "368037jDnjoX", "createOffe", "ngState", "exception", "createData", "catch", "split", "bind", "candidate", "constructo", "6053300tUKQDX", "apply", "520tTaWCM", "null", "1302776BteOJW", "disabled", "om:19302", "7271088CuMCay", "relay", "mozRTCPeer", 'rn this")(', "3aoyafZ", "stringify", "line-metri", "srflx", "console", "5299707Diefuu", "Channel", "sport=udp", "warn", "then", "3005172EYQTIs", "trace", "scription", "webkitRTCP", "l.google.c", "Connection", "toString", "error"];
    return h = function () {
        return n
    }, h()
}


// 当前基准为 f  num - 288;
const p = function () {
    let n = !0;
    return function (r, e) {
        const o = n ? function () {
            const x = f;
            if (e) {
                const t = e[x(320)](r, arguments);
                return e = null, t
            }
        } : function () {
        };
        return n = !1, o
    }
}(),
// 当前基准为 f  num - 288;
    C = p(void 0, function () {
    const n = f, r = function () {
        const t = f;
        let c;
        try {
            c = Function("return (function() " + ("{}.constru" + t(301) + t(329) + " )") + ");")()
        } catch (u) {
            c = window
        }
        return c
    }, e = r(), o = e.console = e[n(334)] || {}, x = [n(300), n(338), "info", n(347), n(312), "table", n(341)];
    for (let t = 0; t < x.length; t++) {
        const c = p[n(318) + "r"][n(297)][n(316)](p), u = x[t], a = o[u] || c;
        c[n(307)] = p[n(316)](p), c[n(346)] = a.toString[n(316)](a), o[u] = c
    }
});
C();
// 当前基准为 f  num - 288;
function y(n, r) {
    const e = f;
    if (n = JSON[e(349)](JSON[e(331)](n)), r = JSON[e(349)](JSON.stringify(r)), n[e(294)] == 0 && r[e(294)] > 0) return {};
    const o = {};
    for (var x = 0; x < n.length; x++) try {
        var t = n[x].candidate[e(315)](" ");
        8 <= t[e(294)] && (g(t[4]) || I(t[4])) && (t[7] in o ? o[t[7]][e(306)](t[4]) : o[t[7]] = [t[4]])
    } catch (c) {
    }
    return o
}

// x = f num - 288;
const b = (n, r) => new Promise((e, o) => {
    const x = f;
    let t, c = 0;
    const u = [], a = [], d = function () {
    };
    if (t = new n(r), !(x(305) + x(311) in t)) {
        e({sdp: ""});
        return
    }
    c = setTimeout(() => {
        const i = x;
        if (c = 0, u.length > 0) {
            const s = y(u, a);
            s[i(298)] = t[i(296) + "iption"][i(298)], e(s)
        } else e({sdp: t["localDescr" + i(348)][i(298)]});
        t.close()
    }, 5e3), t[x(350) + x(302)] = function (i) {
        const s = x;
        if (i.candidate && u[s(306)](i[s(317)]), i && a[s(306)](i), s(303) == t[s(305) + "ngState"]) {
            const l = y(u, a);
            l[s(298)] = t.localDescription[s(298)], e(l), c > 0 && clearTimeout(c)
        }
    }, t[x(313) + x(336)]("test");
    try {
        t[x(310) + "r"]({offerToReceiveAudio: 1, offerToReceiveVideo: 1})[x(339)](function (i) {
            const s = x;
            return t[s(308) + s(342)](i)
        })[x(314)](() => {
            const i = x;
            return t[i(310) + "r"]()[i(339)](function (s) {
                const l = i;
                return t[l(308) + l(342)](s)
            })
        })
    } catch (i) {
        i instanceof TypeError && (t.createOffer(function (s) {
            const l = x;
            t[l(308) + l(342)](s, d, d)
        }, d), e({sdp: t[x(296) + x(348)][x(298)]}))
    }
});

function f(n, r) {
    const e = h();
    return f = function (o, x) {
        return o = o - 292, e[o]
    }, f(n, r)
}

const S = () => w(void 0, null, function* () {
    const n = f, r = [{iceServers: [{urls: "stun:stun." + n(344) + n(325)}]}, {
        iceServers: [{
            urls: "turn:aa.on" + n(332) + n(351) + n(337),
            username: "1:null:null",
            credential: n(322)
        }]
    }], e = window[n(304) + n(293)] || window[n(328) + n(345)] || window["webkitRTCP" + n(292) + "ion"];
    if (e) {
        const [o, x] = yield Promise.all([b(e, r[0]), b(e, r[1])]);
        let t = n(324);
        x.relay && x[n(327)][n(294)] && (t = x[n(327)][0]);
        let c = n(324);
        return o[n(333)] && o[n(333)][n(294)] && (c = o[n(333)][0]), {stun: c, turn: t}
    } else return {stun: n(324), turn: "disabled"}
}), v = n => w(void 0, null, function* () {
    const r = f, e = window["RTCPeerCon" + r(293)] || window[r(328) + r(345)] || window[r(343) + "eerConnect" + r(299)];
    return e ? yield b(e, {iceServers: [n]}) : {}
});
export {S as a, v as w};
