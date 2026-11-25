# mm_flbus.py - FLBus 1.0.1: the shared bus of the =FL= server scripts, on a Battlefield 2 server - as a Multiplay
# ModManager module (ModManager 1.0 or later, Python 2.3 of BF2 1.5)
#
# What it is: the =FL= scripts that watch projectiles (c4clear, claycap, spawnclay, texmine; baseheal) do not ask
# the game for anything themselves - they ask the bus, and the bus asks the game once for all of them:
#   - one timer, every frame: each script is called at its own pace (c4clear every 0.03 s, ...); an error in one does
#     not stop the others; the time each one takes goes into its own load line;
#   - projectiles by kind (C4, claymores, AT mines): asked for by their templates (the names seen on the server, from
#     the start); every projectile is looked at every TYPE_EVERY 5 s (new names; a check of the templates' lists) - or
#     every frame, when a script wants all of them;
#   - one record of each object for every script (where it is, whether it moves, how fast, since when it lies still;
#     an object the game uses again or takes away);
#   - the players once a frame at most, when a script asks (alive, where, the vehicle a soldier is in - the game is never
#     asked for all vehicles: that breaks mm_noarmor_v2, see baseshield 2.0.14);
#   - the map: the flags the game shows, the layout, the built-in flags and spawn points;
#   - the ways to remove an object (down / lift / cut / sky), each checked and logged in the script's own log;
#   - round start and end, game events, chat.
# A script that uses it says so in __required_modules__ ({'mm_flbus': 1.0}): ModManager then loads the bus itself, first.
#
# INSTALL
#   1. Copy this file to <server folder>/admin/modules/mm_flbus.py (next to the scripts that use it).
#   2. Nothing in modmanager.con is needed (ModManager loads it for a script that needs it); a line
#      modmanager.loadModule "mm_flbus" before the scripts' lines does no harm.
#   3. Restart the server (the bus cannot be reloaded).
#   4. flbus.log (server folder): "flbus 1.0.1 loaded", the scripts that joined it, each round's start and its load.
#
# Settings (modmanager.con, mm_flbus.<NAME>): the ways to remove (REMOVE_DEPTH, AWAY_SIDE, LIFT_UP, WAIT_RADIUS, SKY_UP,
# GIVE_UP, GHOST_WAIT) are the same for every script.
#
# History
# 1.0.1 (2026-11-08) For claycap 2.0.0, spawnclay 2.0.0 and texmine 2.0.0: a script can do without the ghost check
#   (ghost_check 0: a claymore sent under the map counts as removed at once, as claycap 1.x - claymores went for good
#   in the 07.11 test); the AT mines told by "mine" in their template's name (as texmine), claymores told first; a chat
#   line longer than 180 characters is split (a 297-character line crashed the server: baseshield 2.0.2).
# 1.0.0 (2026-11-08) Sagara: "let us make a bus script for all scripts of this kind, and then all the rest as separate
#   scripts"; the scripts do not work without it; everything shared in it. First on it: c4clear 2.0.0. The load test
#   (64 players, 5 modules): 4,843 calls into the game a second in a round, 11,816 after a server start (each module
#   looked at every projectile until it had seen its first object).

__version__ = 1.01

__required_modules__ = {
	'modmanager': 1.0
}

__supports_reload__ = False

__supported_games__ = {
	'bf2': True,
	'bf2142': False,
	'bfheroes': False,
	'bfp4f': False
}

__description__ = 'FLBus v1.0.1 (ModManager module)'

import bf2
import host
import sys

VERSION = '1.0.1'

# ------------------------------------------------------------------ settings
FRAME_EVERY = 0.02     # s: the bus's timer (the server's frame is ~0.03 s: every frame)
TYPE_EVERY = 5.0       # s: every projectile is looked at this often (new names; a check of the templates' lists)
STILL_SLOW = 5.0       # s: an object that has lain still this long (and is not being removed) ...
SLOW_EVERY = 1.0       # s: ... is looked at only this often
REMOVE_DEPTH = 1000.0  # m: "under the map" is this far under where it is
AWAY_SIDE = 0.0        # m: ... and this far to the east as well (e.g. 3000: off the map - a test)
LIFT_UP = 1.0          # m: way 2 lifts it this much (0: not tried)
WAIT_RADIUS = 10.0     # m: way 3 (0 health where it lies) only when nobody at all and no vehicle is this close
SKY_UP = 300.0         # m: way 4 sends it this far up (0: not tried)
GIVE_UP = 600.0        # s: an object not removed after this long is left alone (one kept in the sky: never)
GHOST_WAIT = 0.5       # s: one sent under the map that has not moved on there in this long is a ghost (it had stuck)
LOG_FILE = 'flbus.log'

# the kinds of projectiles: the template names seen on the server (asked for from the start) and the words that tell one
KINDS = {
    'c4': (['c4_explosives_Projectile'], ['c4']),
    'claymore': (['usmin_claymore_Projectile'], ['claymore']),
    'atmine': (['at_mine_Projectile'], ['mine']),
}
KIND_ORDER = ['claymore', 'c4', 'atmine']   # a name is told by the first kind whose word it holds
VEHICLE_WORDS = ['jep_', 'apc_', 'tnk_', 'aav_', 'ahe_', 'the_', 'air_', 'boat']   # in the names of vehicles' templates

GP_TYPE = 'dice.hfe.world.ObjectTemplate.GenericProjectile'
CP_TYPE = 'dice.hfe.world.ObjectTemplate.ControlPoint'
BELOW_MAP = -100.0     # m: an object lower than this has been taken under the map
SUNK = 30.0            # m: one this far under where it lay has fallen through the ground
JUMP = 20.0            # m: one that moves this far between two looks is used again by the game (a new one)
SIDEWAYS = 3.0         # m: one being removed that moves this far sideways between two looks: a new one

# ------------------------------------------------------------------ log, chat, time
def write_log(path, text):
    if not path:
        return
    try:
        f = open(path, 'a')
        try:
            try:
                import time
                stamp = time.strftime('%Y-%m-%d %H:%M:%S')
            except:
                stamp = '%.1f' % host.timer_getWallTime()
            f.write('%s  %s\n' % (stamp, text))
        finally:
            f.close()
    except:
        pass

def log(text):
    write_log(LOG_FILE, text)

def err_text():
    t, v, tb = sys.exc_info()
    line = '?'
    try:
        while tb.tb_next:
            tb = tb.tb_next
        line = str(tb.tb_lineno)
    except:
        pass
    return '%s: %s (line %s)' % (t, v, line)

CHAT_MAX = 180         # characters: a longer chat line is split (a 297-character one crashed the server)

def say(text):
    try:
        text = str(text).replace('"', "'")
        parts = []
        while len(text) > CHAT_MAX:
            cut = text.rfind(' ', 0, CHAT_MAX)
            if cut < CHAT_MAX / 3:
                cut = CHAT_MAX
            parts.append(text[:cut])
            text = '  ' + text[cut:].lstrip()
        parts.append(text)
        for x in parts:
            host.rcon_invoke('game.sayAll "%s"' % x)
    except:
        log('chat failed: ' + err_text())

def fmt(msg, args):
    # a message with its %s filled in; a message edited so that it does not fit is said as it is
    try:
        return msg % args
    except:
        return msg

def now():
    return host.timer_getWallTime()

try:
    import time as _time
    _clock = getattr(_time, 'clock', None) or getattr(_time, 'perf_counter', None)
except:
    _clock = None

def clock():
    if _clock is not None:
        try:
            return _clock()
        except:
            pass
    return now()

def apart(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2])

def dist3(a, x, h, z):
    return ((a[0] - x) ** 2 + (a[1] - h) ** 2 + (a[2] - z) ** 2) ** 0.5

def parked_at(p):
    return abs(p[0]) + abs(p[1]) + abs(p[2]) < 0.01

def obj_key(o):
    try:
        return o.token
    except:
        return None

def tpl_name(o):
    try:
        return o.templateName
    except:
        return '?'

# ------------------------------------------------------------------ the scripts on the bus
class Feature:
    # one script on the bus. It sets: maps ('all' or names), every (s), look(t), and if it wants: round_start(t),
    # round_end(t), want_all (1: every projectile every frame), ghost_check (0: one sent under the map counts as removed
    # at once), on_removed(rec, how, t), on_sky(rec, t), on_ghost(rec, t), on_gone(rec, t), on_gave_up(rec, t)
    def __init__(self, name, label, log_file, tag):
        self.name, self.label, self.log_file, self.tag = name, label, log_file, tag
        self.maps = 'all'
        self.every = 0.1
        self.look = None
        self.round_start = None
        self.round_end = None
        self.want_all = 0
        self.ghost_check = 1
        self.on_removed = None
        self.on_sky = None
        self.on_ghost = None
        self.on_gone = None
        self.on_gave_up = None
        self.test_chat = 0
        self.active = 0
        self.last = -99.0
        self.warned = {}
        self.load = [0, 0.0, 0.0]      # looks, s, the longest

    def log(self, text):
        write_log(self.log_file, text)

    def say(self, text):
        say(text)

    def test_say(self, text):
        if self.test_chat:
            say('[%s test] %s' % (self.tag, text))

    def warn_once(self, text):
        if text not in self.warned:
            self.warned[text] = 1
            self.log(text)

    def load_line(self, t):
        ld = self.load
        if not ld[0]:
            return 'load this round: no looks'
        return 'load this round: %d looks in %.0f s, %.2f ms each on average, %.1f ms the longest (with the bus\'s ' \
               'reading of the game for it)' % (ld[0], t - S['round_t'], ld[1] / ld[0] * 1000.0, ld[2] * 1000.0)

FEATURES = []

def feature(name, label, log_file, tag):
    # a script joins the bus: -> its Feature (set its fields, then add(f))
    for f in FEATURES:
        if f.name == name:
            return f
    return Feature(name, label, log_file, tag)

def joined(f):
    log('%s joined (looks every %.2f s; maps: %s%s)' % (f.name, f.every, f.maps,
        (f.want_all and '; every projectile every frame') or ''))

def add(f):
    if f not in FEATURES:
        FEATURES.append(f)
        if S['on']:
            joined(f)       # (one that joins before the bus has started: logged when it starts, with its settings)
    if S['running']:
        start_feature(f, now())

def watched(f, mp):
    m = (f.maps or '').strip().lower()
    if m == 'all':
        return 1
    for x in m.split(','):
        if x.strip() == mp:
            return 1
    return 0

def start_feature(f, t):
    f.active = watched(f, S['map'])
    f.last = -99.0
    f.load = [0, 0.0, 0.0]
    if not f.active:
        f.log('round on %s: not one of the maps watched (MAPS %s) - idle' % (S['map'], f.maps))
        return
    if f.round_start is not None:
        try:
            f.round_start(t)
        except:
            f.warn_once('round start: error: ' + err_text())

# ------------------------------------------------------------------ state
S = {'on': 0, 'timer': None, 'running': 0, 'map': None, 'round_t': 0.0, 'warned': {}, 'mm': None,
     'ticks': [0, 0.0, 0.0]}

def warn_once(text):
    if text not in S['warned']:
        S['warned'][text] = 1
        log(text)

# ------------------------------------------------------------------ projectiles
SC = {'all': None, 'all_t': None, 'by': {}, 'by_t': None, 'tk': {}, 'kind_of': {}, 'tpl': {}, 'tpl_on': {},
      'tpl_bad': {}, 'type_t': -99.0, 'chk_t': -99.0, 'n_all': 0, 'n_tpl': 0}

def seed_kinds():
    for k in KINDS.keys():
        SC['tpl'][k] = {}
        for n in KINDS[k][0]:
            SC['tpl'][k][n] = 1
        SC['tpl_on'][k] = len(KINDS[k][0]) > 0
        SC['tpl_bad'][k] = 0

def kind_of(name):
    k = SC['kind_of'].get(name, 0)
    if k != 0:
        return k
    n = name.lower()
    k = None
    order = KIND_ORDER[:]
    for kk in KINDS.keys():
        if kk not in order:
            order.append(kk)
    for kk in order:
        for w in KINDS[kk][1]:
            if n.find(w) >= 0:
                k = kk
                break
        if k is not None:
            break
    SC['kind_of'][name] = k
    return k

def all_projectiles(t):
    # [(object, key, template name)] of every projectile in the game, read once a frame at most
    if SC['all_t'] == t and SC['all'] is not None:
        return SC['all']
    try:
        objs = bf2.objectManager.getObjectsOfType(GP_TYPE)
    except:
        warn_once('getObjectsOfType failed: ' + err_text())
        objs = []
    old = SC['tk']
    tk = {}
    out = []
    for o in objs:
        k = obj_key(o)
        name = None
        if k is not None:
            name = old.get(k)
        if name is None:
            try:
                name = o.templateName
            except:
                continue
        if k is not None:
            tk[k] = name
        out.append((o, k, name))
    SC['tk'], SC['all'], SC['all_t'] = tk, out, t
    SC['type_t'] = t
    SC['n_all'] = SC['n_all'] + 1
    if t - SC['chk_t'] >= TYPE_EVERY:
        SC['chk_t'] = t
        check_templates(out, t)
    return out

def split(kind):
    out = []
    for o, k, name in SC['all'] or []:
        if kind_of(name) == kind:
            out.append((o, k))
    return out

def by_template(kind):
    # [(object, key)] of the kind's templates, or None if the game cannot be asked so
    out = []
    keys = {}
    names = list(SC['tpl'].get(kind, {}).keys())
    names.sort()
    for name in names:
        try:
            objs = bf2.objectManager.getObjectsOfTemplate(name)
        except:
            return None
        SC['n_tpl'] = SC['n_tpl'] + 1
        for o in objs:
            k = obj_key(o)
            if k is not None:
                if k in keys:
                    continue
                keys[k] = 1
            out.append((o, k))
    return out

def tpl_off(kind, why):
    if SC['tpl_bad'].get(kind):
        return
    SC['tpl_on'][kind] = 0
    SC['tpl_bad'][kind] = 1
    log('%s: every projectile looked at again, every frame it is asked for (%s)' % (kind, why))

def check_templates(out, t):
    # the names seen of each kind; the templates' lists checked against every projectile
    seen = {}
    for o, k, name in out:
        kk = kind_of(name)
        if kk is None or kk not in KINDS:
            continue
        L = seen.get(kk)
        if L is None:
            L = []
            seen[kk] = L
        L.append(k)
        if name not in SC['tpl'][kk]:
            SC['tpl'][kk][name] = 1
            log('%s template: %s' % (kk, name))
    for kk in seen.keys():
        if SC['tpl_bad'].get(kk):
            continue
        T = by_template(kk)
        if T is None:
            tpl_off(kk, 'getObjectsOfTemplate failed')
            continue
        have = {}
        for o, k in T:
            have[k] = 1
        miss = 0
        for k in seen[kk]:
            if k is None or k not in have:
                miss = miss + 1
        if miss:
            tpl_off(kk, "the template's list lacked %d of %d" % (miss, len(seen[kk])))
        elif not SC['tpl_on'].get(kk):
            SC['tpl_on'][kk] = 1
            log('%s: from now on asked for by their templates' % kk)

def objects(kind, t):
    # [(object, key)] of a kind this frame
    if SC['by_t'] != t:
        SC['by'] = {}
        SC['by_t'] = t
    L = SC['by'].get(kind)
    if L is not None:
        return L
    if SC['all_t'] == t and SC['all'] is not None:
        L = split(kind)
    elif SC['tpl_on'].get(kind) and t - SC['type_t'] < TYPE_EVERY:
        L = by_template(kind)
        if L is None:
            tpl_off(kind, 'getObjectsOfTemplate failed')
    if L is None:
        all_projectiles(t)
        L = split(kind)
    SC['by'][kind] = L
    return L

# ------------------------------------------------------------------ one record of each object, for every script
TR = {}

def new_rec(kind, T, t, pos, o, k):
    T['serial'] = T['serial'] + 1
    r = {'kind': kind, 'id': '#%d' % T['serial'], 'o': o, 'key': k, 't0': t, 'p_first': pos, 'pos': pos, 'last': pos,
         'last_t': t, 'still': t, 'moved': 0, 'upd': 1, 'vel': None, 'track': [(t, pos[1])], 'parked': 0, 'seen_t': t,
         'x': {}, 'rm': None, 'new': 1}
    if parked_at(pos):
        r['parked'] = 1
    else:
        T['seen'] = T['seen'] + 1
    return r

def tracker(kind):
    T = TR.get(kind)
    if T is None:
        T = {'recs': {}, 't': None, 'list': [], 'serial': 0, 'seen': 0}
        TR[kind] = T
    return T

def seen_n(kind):
    return tracker(kind)['seen']

def slow_now(r, t):
    if SLOW_EVERY <= 0 or t - r['seen_t'] >= SLOW_EVERY - 0.001 or r['parked']:
        return 0
    rm = r['rm']
    if rm is not None:
        return rm['done'] and t - rm['done_t'] > 30.0
    return t - r['still'] >= STILL_SLOW

def track(kind, t):
    # [record] of the objects of a kind in the game now (not those parked at 0,0,0); updated once a frame
    T = tracker(kind)
    if T['t'] == t:
        return T['list']
    T['t'] = t
    recs = T['recs']
    seen = {}
    out = []
    for o, k in objects(kind, t):
        r = None
        if k is not None:
            r = recs.get(k)
            if r is not None and slow_now(r, t):
                seen[k] = 1
                r['o'], r['upd'], r['moved'], r['new'] = o, 0, 0, 0
                out.append(r)
                continue
        try:
            pos = o.getPosition()
            pos = (float(pos[0]), float(pos[1]), float(pos[2]))
        except:
            continue
        if k is None:
            # (no token: the same object = the one seen last time within 0.6 m)
            for kk in recs.keys():
                if kk not in seen and apart(recs[kk]['last'], pos) < 0.6:
                    k = kk
                    break
            if k is None:
                T['serial'] = T['serial'] + 1
                k = 'n%d' % T['serial']
        seen[k] = 1
        parked = parked_at(pos)
        r = recs.get(k)
        if r is None:
            r = new_rec(kind, T, t, pos, o, k)
            recs[k] = r
        elif not parked:
            last = r['last']
            again = r['parked']
            if not again and last[1] < BELOW_MAP and pos[1] > BELOW_MAP:
                again = 1          # (back from under the map)
            if not again and last[1] > BELOW_MAP and pos[1] > BELOW_MAP:
                if r['rm'] is None:
                    again = apart(last, pos) > JUMP
                else:
                    again = abs(pos[0] - last[0]) + abs(pos[2] - last[2]) > SIDEWAYS
            if again:
                # the game uses the object again (from 0,0,0, from under the map, from somewhere else): a new one
                rm = r['rm']
                if rm is not None and not rm['done']:
                    rm['by'].log('%s %s: used again by the game for a new one %.1f s after it was found - not removed '
                                 '(ways tried: %s)' % (rm['by'].label, r['id'], t - rm['t'], tries_text(r)))
                gone(r, t)
                r = new_rec(kind, T, t, pos, o, k)
                recs[k] = r
            else:
                r['new'] = 0
        else:
            r['new'] = 0
        r['o'], r['seen_t'], r['upd'] = o, t, 1
        if parked:
            rm = r['rm']
            if rm is not None and not r['parked'] and not rm['done']:
                rm['by'].log('%s %s: taken away by the game (to 0,0,0) %.1f s after it was found' % (rm['by'].label,
                             r['id'], t - rm['t']))
            r['parked'] = 1
            r['last'] = pos
            continue
        r['moved'] = apart(r['last'], pos) > 0.05
        if r['moved']:
            dt = t - r['last_t']
            r['vel'] = None
            if dt > 0.001 and dt < 0.35 and r['last'][1] > BELOW_MAP and pos[1] > BELOW_MAP:
                r['vel'] = ((pos[0] - r['last'][0]) / dt, (pos[1] - r['last'][1]) / dt, (pos[2] - r['last'][2]) / dt)
                if r['rm'] is None and t - r['t0'] <= 3.0 and len(r['track']) < 60:
                    r['track'].append((t, pos[1]))
            r['still'] = t
        r['pos'] = pos
        r['last'] = pos
        r['last_t'] = t
        if r['rm'] is not None:
            follow_up(r, pos, t)
        out.append(r)
    for k in list(recs.keys()):
        if k not in seen:
            r = recs[k]
            rm = r['rm']
            if rm is not None and not rm['done'] and not r['parked']:
                st = rm['step']
                if (st in ('cut', 'sky+cut') and t - rm['step_t'] < 2.0) or rm['under'] is not None:
                    removed(r, '%s: gone from the game' % st, t)
                else:
                    rm['by'].log('%s %s: gone from the game %.1f s after it was found (it went off?) - not removed by '
                                 'the script (ways tried: %s)' % (rm['by'].label, r['id'], t - rm['t'], tries_text(r)))
                    rm['by'].test_say('%s %s is gone (it went off?)' % (rm['by'].label, r['id']))
            gone(r, t)
            del recs[k]
    T['list'] = out
    return out

def gone(r, t):
    # a record has ended: every script that kept something on it is told
    for f in FEATURES:
        if f.name in r['x'] and f.on_gone is not None:
            try:
                f.on_gone(r, t)
            except:
                f.warn_once('on_gone: error: ' + err_text())

# ------------------------------------------------------------------ players and vehicles
PL = {'t': None, 'list': [], 'veh': None, 'veh_t': None, 'notveh': {}}

def players(t=None):
    # [{'p', 'alive', 'pos', 'soldier', 'veh'}] once a frame at most: pos - where he is (his vehicle's place if he is in
    # one); veh - the vehicle he is in (its root object), or None
    if t is None:
        t = now()
    if PL['t'] == t:
        return PL['list']
    out = []
    try:
        ps = bf2.playerManager.getPlayers()
    except:
        ps = []
    for p in ps:
        d = {'p': p, 'alive': 0, 'pos': None, 'soldier': None, 'veh': None}
        try:
            d['alive'] = p.isAlive()
        except:
            pass
        if d['alive']:
            try:
                s = p.getDefaultVehicle()
                d['soldier'] = s
                v = p.getVehicle()
                r = None
                if v is not None:
                    try:
                        r = bf2.objectManager.getRootParent(v)
                    except:
                        r = root_of(v)
                if r is not None and obj_key(r) is not None and obj_key(r) != obj_key(s):
                    d['veh'] = r
                    q = r.getPosition()
                else:
                    q = s.getPosition()
                d['pos'] = (float(q[0]), float(q[1]), float(q[2]))
            except:
                pass
        out.append(d)
    PL['t'], PL['list'] = t, out
    return out

def someone_near(pos, r, t=None):
    for d in players(t):
        q = d['pos']
        if q is not None and dist3(pos, q[0], q[1], q[2]) <= r:
            return 1
    return 0

def soldier_keys(t=None):
    out = {}
    for d in players(t):
        if d['soldier'] is not None:
            k = obj_key(d['soldier'])
            if k is not None:
                out[k] = 1
    return out

def parent_of(o):
    try:
        return o.getParent()
    except:
        return None

def root_of(o):
    n = 0
    while n < 10:
        q = parent_of(o)
        if q is None:
            return o
        o = q
        n = n + 1
    return o

def is_vehicle(name):
    n = name.lower()
    for w in VEHICLE_WORDS:
        if n.find(w) >= 0:
            return 1
    if n not in PL['notveh']:
        PL['notveh'][n] = 1
        log('not taken as a vehicle: %s' % name)
    return 0

def vehicles(t=None):
    # [object] of the vehicles soldiers are in now (from the players: never every PlayerControlObject), once a second
    if t is None:
        t = now()
    if PL['veh'] is not None and t - PL['veh_t'] < 1.0:
        return PL['veh']
    out = []
    keys = {}
    for d in players(t):
        v = d['veh']
        if v is None:
            continue
        k = obj_key(v)
        if k in keys:
            continue
        keys[k] = 1
        if is_vehicle(tpl_name(v)):
            out.append(v)
    PL['veh'], PL['veh_t'] = out, t
    return out

def vehicle_near(pos, r, t=None):
    # (the vehicle's template, m) of the nearest vehicle with soldiers in it within r m, or None
    best = None
    for v in vehicles(t):
        try:
            q = v.getPosition()
        except:
            continue
        d = dist3(pos, q[0], q[1], q[2])
        if d <= r and (best is None or d < best[1]):
            best = (v, d)
    if best is None:
        return None
    return tpl_name(best[0]), best[1]

def clear_around(pos, t=None):
    # 1 if nobody at all and no vehicle with soldiers in it is within WAIT_RADIUS
    return not someone_near(pos, WAIT_RADIUS, t) and vehicle_near(pos, WAIT_RADIUS, t) is None

# ------------------------------------------------------------------ the map: flags, layout, spawn points
MP = {'layout': None, 'ready': 0, 'try_t': -99.0, 'game_flags': 0, 'noflags': 0}

def game_flags():
    out = []
    try:
        objs = bf2.objectManager.getObjectsOfType(CP_TYPE)
    except:
        objs = []
    for cp in objs:
        try:
            p = cp.getPosition()
            out.append((float(p[0]), float(p[1]), float(p[2])))
        except:
            pass
    return out

def match_layout(mp, cps):
    lay = PLACES.get(mp, {})
    keys = list(lay.keys())
    keys.sort()
    for key in keys:
        F = lay[key]['flags']
        if len(F) != len(cps):
            continue
        ok = 1
        for p in cps:
            hit = 0
            for f in F:
                if (f[2] - p[0]) ** 2 + (f[4] - p[2]) ** 2 <= 9.0:
                    hit = 1
                    break
            if not hit:
                ok = 0
                break
        if ok:
            return key, lay[key]
    return None

def known_layouts(mp):
    L = []
    lay = PLACES.get(mp, {})
    for key in lay.keys():
        L.append('%s (%d flags)' % (key, len(lay[key]['flags'])))
    L.sort()
    return ', '.join(L)

def layout(t=None):
    # None: not known yet (the game shows no flags yet, or they may still be coming in - the first minute of a round);
    # else {'key': the layout (None: no data for it), 'flags': [(id, name, x, h, z, radius, main)], 'points': [(name,
    # flag id, x, h, z)], 'game_flags': how many the game shows}
    if MP['ready']:
        return MP['layout']
    if t is None:
        t = now()
    if t - MP['try_t'] < 2.0:
        return None
    MP['try_t'] = t
    cps = game_flags()
    if not cps:
        if t - S['round_t'] > 60 and not MP['noflags']:
            MP['noflags'] = 1
            log('round on %s: the game shows no flags - the layout cannot be told' % S['map'])
        return None
    m = match_layout(S['map'], cps)
    if m is None:
        if t - S['round_t'] < 60:
            return None
        MP['layout'] = {'key': None, 'flags': [], 'points': [], 'game_flags': len(cps)}
        MP['ready'] = 1
        log('round on %s: no data for this layout (the game shows %d flags; the bus knows: %s)' % (S['map'], len(cps),
            known_layouts(S['map']) or 'nothing for this map'))
        return MP['layout']
    key, D = m
    MP['layout'] = {'key': key, 'flags': D['flags'], 'points': D['points'], 'game_flags': len(cps)}
    MP['ready'] = 1
    log('round on %s: layout %s (%d flags, %d spawn points)' % (S['map'], key, len(D['flags']), len(D['points'])))
    return MP['layout']

# ------------------------------------------------------------------ the ways to remove an object
def remove(f, r, t, what):
    # a script asks for an object to be removed; what: where it is, for the logs ("near the spawn point ...")
    pos = r['pos']
    r['rm'] = {'by': f, 't': t, 'pos0': pos, 'what': what, 'step': None, 'step_t': -99.0, 'step_pos': pos, 'n': {},
               'done': None, 'done_t': 0.0, 'noted': {}, 'sky_ok': 0, 'landed': 0, 'gaveup': 0, 'off_t': -99.0,
               'offhow': None, 'moveerr': 0, 'offerr': 0, 'sky_t': 0.0, 'way': None, 'last_cut': None, 'under': None,
               'ghost': 0}
    do_step(r, 'down', pos, t)

def wrappers(o):
    # the object, and the same object as the game gives it by its template (one more way to reach it)
    out = [o]
    k = obj_key(o)
    if k is None:
        return out
    try:
        for x in bf2.objectManager.getObjectsOfTemplate(o.templateName):
            if obj_key(x) == k and x is not o:
                out.append(x)
    except:
        pass
    return out

def move(r, to, every):
    rm = r['rm']
    ws = [r['o']]
    if every:
        ws = wrappers(r['o'])
    for w in ws:
        try:
            w.setPosition(to)
        except:
            if not rm['moveerr']:
                rm['moveerr'] = 1
                rm['by'].log('%s %s: setPosition failed: %s' % (rm['by'].label, r['id'], err_text()))

def func_of(bm):
    f = getattr(bm, 'im_func', None)
    if f is None:
        f = getattr(bm, '__func__', None)
    return f

def borrowed_set():
    # the function behind a living soldier's setDamage (it sets an object's health - the game hands out some objects
    # without a setDamage of their own)
    for d in players():
        if not d['alive'] or d['soldier'] is None:
            continue
        try:
            f = func_of(d['soldier'].setDamage)
        except:
            continue
        if f is not None:
            return f
    return None

def set_off(r):
    rm = r['rm']
    o = r['o']
    rm['off_t'] = now()
    own = getattr(o, 'setDamage', None)
    how = 'its own setDamage'
    try:
        if own is not None:
            own(0.0)
        else:
            f = borrowed_set()
            if f is None:
                if not rm['offerr']:
                    rm['offerr'] = 1
                    rm['by'].log('%s %s has no setDamage and there is no soldier\'s to use' % (rm['by'].label, r['id']))
                return
            how = "a soldier's setDamage"
            f(o, 0.0)
    except:
        if not rm['offerr']:
            rm['offerr'] = 1
            rm['by'].log('%s %s: setDamage failed (%s): %s' % (rm['by'].label, r['id'], how, err_text()))
        return
    if not rm['offhow']:
        rm['offhow'] = how
        rm['by'].log('%s %s set to 0 health with %s' % (rm['by'].label, r['id'], how))

def note(r, key, text):
    rm = r['rm']
    if key in rm['noted']:
        return
    rm['noted'][key] = 1
    rm['by'].log('%s %s: %s' % (rm['by'].label, r['id'], text))
    rm['by'].test_say('%s %s: %s' % (rm['by'].label, r['id'], text))

def n_of(r, name):
    return r['rm']['n'].get(name, 0)

def do_step(r, name, pos, t):
    rm = r['rm']
    rm['step'], rm['step_t'], rm['step_pos'], rm['way'] = name, t, pos, name
    rm['n'][name] = rm['n'].get(name, 0) + 1
    if name in ('down', 'lift+down', 'sky+down'):
        move(r, (pos[0] + AWAY_SIDE, pos[1] - REMOVE_DEPTH, pos[2]), rm['n'][name] > 1)
    elif name == 'lift':
        move(r, (pos[0], pos[1] + LIFT_UP, pos[2]), 0)
    elif name == 'sky':
        rm['sky_t'] = t
        move(r, (pos[0], pos[1] + SKY_UP, pos[2]), 0)
    elif name in ('cut', 'sky+cut'):
        rm['last_cut'] = name
        set_off(r)

def tries_text(r):
    L = []
    for k in ['down', 'lift', 'lift+down', 'cut', 'sky', 'sky+cut', 'sky+down']:
        if n_of(r, k):
            L.append('%s %d' % (k, n_of(r, k)))
    return ', '.join(L) or 'none'

def call(f, what, *args):
    fn = getattr(f, what, None)
    if fn is None:
        return
    try:
        fn(*args)
    except:
        f.warn_once('%s: error: %s' % (what, err_text()))

def removed(r, how, t):
    rm = r['rm']
    rm['done'], rm['done_t'] = how, t
    f = rm['by']
    f.log('%s %s (%s): REMOVED (%s) %.1f s after it was found' % (f.label, r['id'], rm['what'], how, t - rm['t']))
    f.test_say('%s %s REMOVED (%s)' % (f.label, r['id'], how))
    call(f, 'on_removed', r, how, t)

def ghost(r, t):
    rm = r['rm']
    rm['done'], rm['done_t'], rm['ghost'] = 'ghost', t, 1
    f = rm['by']
    f.log('%s %s (%s): a ghost - moved only on paper: it does not move on from where it was sent (it had stuck): it is '
          'still where it was and still goes off there; nothing more tried, nothing said' % (f.label, r['id'], rm['what']))
    f.test_say('%s %s: a ghost - it had stuck, still there' % (f.label, r['id']))
    call(f, 'on_ghost', r, t)

def next_step(r, pos, t):
    rm = r['rm']
    if not n_of(r, 'down'):
        return 'down'
    if LIFT_UP > 0 and not n_of(r, 'lift'):
        return 'lift'
    if not n_of(r, 'cut') and clear_around(pos, t):
        return 'cut'
    if SKY_UP > 0 and (rm['sky_ok'] or n_of(r, 'sky') < 3):
        return 'sky'
    if t - rm['step_t'] < 2.0:
        return None
    if LIFT_UP > 0 and n_of(r, 'lift') < 3:
        return 'lift'
    if n_of(r, 'cut') < 10 and clear_around(pos, t):
        return 'cut'
    return 'down'

def follow_up(r, pos, t):
    # an object being removed, every frame while the game still has it
    rm = r['rm']
    f = rm['by']
    if rm['ghost']:
        return
    if rm['done']:
        # under the map: set it off there now and then (nobody is near it there), for 30 s
        if pos[1] < BELOW_MAP and t - rm['off_t'] >= 1.0 and t - rm['done_t'] < 30:
            set_off(r)
        return
    st = rm['step']
    if pos[1] < BELOW_MAP:
        if not f.ghost_check:
            removed(r, '%s: under the map' % (rm['way'] or '?'), t)
            return
        # really moved only if it moves on down there (a stuck object sent there only on paper stays where it was put)
        if rm['under'] is None:
            rm['under'] = (pos, t)
            return
        if apart(pos, rm['under'][0]) > 0.05:
            removed(r, '%s: it falls under the map' % (rm['way'] or '?'), t)
        elif t - rm['under'][1] >= GHOST_WAIT:
            ghost(r, t)
        return
    if pos[1] < rm['pos0'][1] - SUNK:
        removed(r, '%s: fell through the ground' % (rm['last_cut'] or rm['way'] or '?'), t)
        return
    if t - rm['t'] > GIVE_UP and not rm['sky_ok']:
        if not rm['gaveup']:
            rm['gaveup'] = 1
            f.log('%s %s (%s): not removed in %.0f s - left alone (ways tried: %s)' % (f.label, r['id'], rm['what'],
                  GIVE_UP, tries_text(r)))
            call(f, 'on_gave_up', r, t)
        return
    dt = t - rm['step_t']
    sp = rm['step_pos']
    if st == 'lift':
        if pos[1] > sp[1] + 0.3:
            note(r, 'lift up', 'lift: it went up (%.1f m) - now under the map from there' % (pos[1] - sp[1]))
            do_step(r, 'lift+down', pos, t)
            return
        if dt < 0.35:
            return
        note(r, 'lift no', 'lift: it did NOT go up (at %.2f, %.2f, %.2f)' % (pos[0], pos[1], pos[2]))
    elif st == 'sky':
        if pos[1] > sp[1] + 10.0:
            if not rm['sky_ok']:
                rm['sky_ok'] = 1
                f.log('%s %s: sky: it went up %.0f m - out of the way' % (f.label, r['id'], pos[1] - sp[1]))
                f.test_say('%s %s: sky: it went up %.0f m' % (f.label, r['id'], pos[1] - sp[1]))
                call(f, 'on_sky', r, t)
            if not n_of(r, 'sky+cut') and not someone_near(pos, WAIT_RADIUS, t):
                do_step(r, 'sky+cut', pos, t)
            elif not n_of(r, 'sky+down'):
                do_step(r, 'sky+down', pos, t)
            else:
                rm['step'], rm['step_t'], rm['step_pos'] = 'falling', t, pos
            return
        if dt < 0.35:
            return
        note(r, 'sky no', 'sky: it did NOT go up (at %.2f, %.2f, %.2f)' % (pos[0], pos[1], pos[2]))
    elif st == 'sky+cut':
        if dt < 1.0:
            return
        note(r, 'sky+cut', 'sky: 0 health up there did nothing (at %.0f m) - now under the map from there' % pos[1])
        do_step(r, 'sky+down', pos, t)
        return
    elif st in ('down', 'lift+down', 'sky+down'):
        if dt < 0.25:
            return
        note(r, st, '%s: put back by the game (at %.2f, %.2f, %.2f)' % (st, pos[0], pos[1], pos[2]))
        if st == 'sky+down':
            rm['step'], rm['step_t'], rm['step_pos'] = 'falling', t, pos
            return
    elif st == 'cut':
        if dt < 1.0:
            return
        if pos[1] < sp[1] - 0.5 and dt < 8.0:
            note(r, 'cut sinks', 'cut: it sinks into the ground (%.1f m under where it lay)' % (sp[1] - pos[1]))
            return
        note(r, 'cut', 'cut: 0 health where it lies did nothing')
    elif st == 'falling':
        if t - r['still'] < 0.2:
            return
        if pos[1] > rm['pos0'][1] + 10.0:
            if t - r['still'] < 2.0:
                return
            removed(r, 'sky: it stays up there', t)
            return
        if not rm['landed']:
            rm['landed'] = 1
            f.log('%s %s: fell back from the sky to (%.2f, %.2f, %.2f) %.1f s after it went up - it is sent up again '
                  'each time it lies on the ground' % (f.label, r['id'], pos[0], pos[1], pos[2], t - rm['sky_t']))
    rm['step'] = None
    name = next_step(r, pos, t)
    if name is None:
        return
    if name == 'sky' and not n_of(r, 'sky') and not n_of(r, 'cut'):
        note(r, 'skip cut', 'cut skipped: somebody or a vehicle is within %.0f m' % WAIT_RADIUS)
    do_step(r, name, pos, t)

# ------------------------------------------------------------------ the frame
def tick(data=None):
    if not S['running']:
        return
    t = now()
    c0 = clock()
    due = []
    for f in FEATURES:
        if f.active and f.look is not None and t - f.last >= f.every - 0.001:
            due.append(f)
    for f in due:
        if f.want_all:
            try:
                all_projectiles(t)
            except:
                warn_once('reading every projectile: ' + err_text())
            break
    for f in due:
        f.last = t
        a = clock()
        try:
            f.look(t)
        except:
            f.warn_once('error: ' + err_text())
        d = clock() - a
        ld = f.load
        ld[0], ld[1] = ld[0] + 1, ld[1] + d
        if d > ld[2]:
            ld[2] = d
    # objects being removed are followed every frame, whoever looks at them
    for kind in TR.keys():
        T = TR[kind]
        if T['t'] == t:
            continue
        busy = 0
        for r in T['recs'].values():
            if r['rm'] is not None and not r['rm']['done']:
                busy = 1
                break
        if busy:
            try:
                track(kind, t)
            except:
                warn_once('following up %s: %s' % (kind, err_text()))
    d = clock() - c0
    tk = S['ticks']
    tk[0], tk[1] = tk[0] + 1, tk[1] + d
    if d > tk[2]:
        tk[2] = d

# ------------------------------------------------------------------ rounds
def start_round():
    end_round()
    try:
        mp = bf2.gameLogic.getMapName().lower()
    except:
        mp = ''
    t = now()
    S['map'], S['round_t'], S['running'] = mp, t, 1
    S['ticks'] = [0, 0.0, 0.0]
    for k in list(TR.keys()):
        del TR[k]
    PL['t'], PL['veh'] = None, None
    MP['layout'], MP['ready'], MP['try_t'], MP['noflags'] = None, 0, -99.0, 0
    SC['all'], SC['all_t'], SC['by'], SC['by_t'], SC['n_all'], SC['n_tpl'] = None, None, {}, None, 0, 0
    names = []
    for f in FEATURES:
        names.append(f.name)
    log('round on %s: scripts on the bus: %s' % (mp, ', '.join(names) or 'none'))
    for f in FEATURES:
        start_feature(f, t)
    layout(t)

def end_round():
    if not S['running']:
        return
    S['running'] = 0
    t = now()
    for f in FEATURES:
        if f.active and f.round_end is not None:
            try:
                f.round_end(t)
            except:
                f.warn_once('round end: error: ' + err_text())
        f.active = 0
    tk = S['ticks']
    if tk[0]:
        parts = []
        for f in FEATURES:
            if f.load[0]:
                parts.append('%s %.2f ms' % (f.name, f.load[1] / f.load[0] * 1000.0))
        log('load this round on %s: %d frames in %.0f s, %.2f ms each on average, %.1f ms the longest (%s); every '
            'projectile read %d times, by template %d times' % (S['map'], tk[0], t - S['round_t'],
            tk[1] / tk[0] * 1000.0, tk[2] * 1000.0, ', '.join(parts) or '-', SC['n_all'], SC['n_tpl']))

def on_status(status):
    if not S['on']:
        return
    try:
        if status == bf2.GameStatus.Playing:
            start_round()
        else:
            end_round()
    except:
        log('status: ' + err_text())

# ------------------------------------------------------------------ game events
EV = {}

def on_event(name, fn):
    # fn(*the event's arguments) for a game event (host.registerHandler), registered with the game once
    L = EV.get(name)
    if L is None:
        L = []
        EV[name] = L
        def disp(*args):
            for g in EV.get(name, []):
                try:
                    g(*args)
                except:
                    warn_once('%s: error: %s' % (name, err_text()))
        try:
            host.registerHandler(name, disp, 1)
        except:
            log('could not register %s: %s' % (name, err_text()))
    if fn not in L:
        L.append(fn)

def bus_init():
    if S['on']:
        return
    S['on'] = 1
    seed_kinds()
    try:
        host.registerGameStatusHandler(on_status)
    except:
        log('could not register: ' + err_text())
    try:
        S['timer'] = bf2.Timer(tick, FRAME_EVERY, 1)
        S['timer'].setRecurring(FRAME_EVERY)
    except:
        log('timer failed: ' + err_text())
    kinds = []
    for k in KINDS.keys():
        kinds.append('%s (%s)' % (k, ', '.join(KINDS[k][0])))
    kinds.sort()
    log('flbus %s loaded (a frame every %.2f s; projectiles asked for by their templates: %s; every projectile every '
        '%.0f s; ways to remove: down %.0f m%s, lift %.1f m + down, cut when nobody and no vehicle is within %.0f m, sky '
        '%.0f m)' % (VERSION, FRAME_EVERY, '; '.join(kinds), TYPE_EVERY, REMOVE_DEPTH,
        (AWAY_SIDE and ' and %.0f m east' % AWAY_SIDE) or '', LIFT_UP, WAIT_RADIUS, SKY_UP))
    for f in FEATURES:
        joined(f)
    playing = 0
    try:
        mm = S['mm']
        st = getattr(mm, 'currentGameStatus', None)
        if st is None:
            st = getattr(bf2, 'currentGameStatus', None)
        playing = st == bf2.GameStatus.Playing
    except:
        pass
    if playing:
        start_round()   # (loaded during a round)


# ------------------------------------------------------------------ data
# each map's places per layout (game mode : size), from the level's GamePlayObjects.con:
#   flags: (the control point's id, name, x, height of the pole's foot, z (north), radius, main base 1)
#   points: (spawn point - CPNAME_SK_64_<name> in the file, the control point's id, x, height, z)
PLACES = {
    'strike_at_karkand': {
        'gpm_cq:64': {'flags': [
            (13, 'Gas Station', -161.03, 161.287, -262.828, 10.0, 1),
            (26, 'Hotel', -194.407, 158.221, 11.417, 5.0, 0),
            (29, 'Square', -220.067, 155.8, 98.08, 10.0, 0),
            (30, 'Train Accident', -122.362, 149.889, 256.638, 6.0, 0),
            (31, 'Gatehouse', 13.954, 155.986, 288.937, 10.0, 0),
            (32, 'Cement Factory', 29.438, 149.985, 164.429, 9.0, 0),
            (33, 'Warehouse', 103.951, 152.696, 231.055, 5.0, 0),
            (34, 'Factory', 183.0, 152.686, 166.0, 10.0, 0),
            (201, 'Suburb', -323.723, 168.393, 220.168, 10.0, 0),
        ], 'points': [
            ('gasstation_1', 13, -160.956, 161.298, -266.017),
            ('gasstation_2', 13, -179.0, 161.298, -316.0),
            ('gasstation_3', 13, -121.763, 161.298, -282.87),
            ('gasstation_4', 13, -160.159, 161.298, -319.513),
            ('hotel_1', 26, -189.799, 155.901, 26.381),
            ('hotel_2', 26, -222.868, 155.9, -3.19),
            ('hotel_3', 26, -189.339, 155.901, 0.623),
            ('hotel_4', 26, -189.354, 155.901, 0.593),
            ('square_1', 29, -244.955, 155.9, 123.388),
            ('square_2', 29, -206.033, 155.9, 106.989),
            ('square_3', 29, -251.064, 155.9, 82.85),
            ('square_4', 29, -247.864, 155.9, 104.546),
            ('trainaccident_2', 30, -121.993, 149.896, 285.918),
            ('trainaccident_3', 30, -146.072, 149.799, 309.503),
            ('trainaccident_4', 30, -161.575, 149.899, 240.567),
            ('trainaccident_5', 30, -119.562, 149.899, 236.872),
            ('gatehouse_1', 31, -9.494, 155.997, 288.467),
            ('gatehouse_3', 31, 49.947, 155.997, 283.354),
            ('gatehouse_4', 31, -6.013, 149.996, 241.044),
            ('gatehouse_5', 31, -16.658, 149.996, 250.747),
            ('cementfactory_2', 32, 12.324, 149.996, 184.576),
            ('cementfactory_4', 32, -16.053, 149.996, 187.962),
            ('cementfactory_5', 32, 10.146, 149.996, 158.871),
            ('factory_1', 34, 213.449, 152.696, 194.756),
            ('factory_2', 34, 216.815, 152.696, 148.816),
            ('factory_3', 34, 163.969, 152.696, 128.307),
            ('factory_4', 34, 166.744, 152.696, 178.324),
            ('factory_5', 34, 186.74, 152.696, 130.638),
            ('warehouse_1', 33, 105.55, 152.802, 215.368),
            ('warehouse_2', 33, 126.526, 152.696, 274.864),
            ('warehouse_3', 33, 121.035, 153.863, 239.183),
            ('warehouse_4', 33, 93.391, 160.865, 246.648),
            ('warehouse_5', 33, 91.745, 159.204, 211.491),
            ('gasstation_6', 13, -171.873, 162.497, -114.155),
            ('gasstation_7', 13, -160.068, 162.497, -131.852),
            ('gasstation_8', 13, -150.157, 162.497, -113.539),
            ('gasstation_9', 13, -236.019, 163.399, -142.858),
            ('gasstation_10', 13, -253.533, 163.399, -139.585),
            ('gasstation_11', 13, -252.868, 163.399, -159.375),
            ('suburb_1', 201, -315.926, 168.42, 236.867),
            ('suburb_2', 201, -355.015, 173.699, 171.518),
            ('suburb_3', 201, -283.31, 167.299, 221.082),
            ('suburb_5', 201, -339.713, 168.699, 223.194),
            ('gasstation_11_0', 13, -231.691, 163.413, -171.932),
            ('gasstation_12', 13, -135.397, 163.769, -132.963),
            ('factory_6', 34, 226.726, 152.696, 160.735),
            ('gatehouse_5_0', 31, 25.624, 155.997, 314.604),
            ('hotel_5', 26, -222.771, 155.9, 14.727),
        ]},
    },
}


# ------------------------------------------------------------------ ModManager interface
# The defaults are the values of the settings above. modmanager.con can override them: mm_flbus.<NAME> <value>
configDefaults = {}
for _k in ['FRAME_EVERY', 'TYPE_EVERY', 'STILL_SLOW', 'SLOW_EVERY', 'REMOVE_DEPTH', 'AWAY_SIDE', 'LIFT_UP', 'WAIT_RADIUS',
           'SKY_UP', 'GIVE_UP', 'GHOST_WAIT', 'LOG_FILE']:
    configDefaults[_k] = globals()[_k]

class FLBus( object ):

    def __init__( self, modManager ):
        self.mm = modManager
        # 0 = new, 1 = running, 2 = shut down (the engine cannot unregister its handler: not reloadable)
        self.__state = 0

    def init( self ):
        if 0 != self.__state:
            return
        cfg = self.mm.getModuleConfig( configDefaults )
        g = globals()
        for k in configDefaults:
            try:
                g[k] = cfg[k]
            except:
                pass
        self.__state = 1
        S['mm'] = self.mm
        bus_init()
        try:
            self.mm.info( 'flbus %s is running (see %s)' % ( VERSION, LOG_FILE or 'no log' ) )
        except:
            pass

    def shutdown( self ):
        self.__state = 2
        end_round()
        S['on'] = 0
        if S['timer'] is not None:
            try:
                S['timer'].destroy()
            except:
                pass
            S['timer'] = None

    def update( self ):
        pass

def mm_load( modManager ):
    return FLBus( modManager )
