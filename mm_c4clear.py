# mm_c4clear.py - C4Clear 2.0.0: C4 thrown where its blast kills soldiers at a spawn point or in a flag's zone is
# removed while it still flies, on a Battlefield 2 server - as a Multiplay ModManager module on the =FL= bus mm_flbus
# (ModManager 1.0 or later, Python 2.3 of BF2 1.5)
#
# It needs mm_flbus.py (1.0 or later) in admin/modules: ModManager loads it by itself (__required_modules__). The bus
# asks the game for the C4, the players, the map's flags and does the removing; this module has only the C4 rule.
#
# The rule (as 1.1.3): a C4 sticks where it lands, and once stuck it cannot be moved for real (Sagara's test of 1.0.0,
# 08.11: "the ghost is dangerous") - so a C4 is caught IN THE AIR. No C4 is touched before it is EARLIEST 0.05 s old
# (moved in its first moment it stays where it is in the players' games - test of 1.1.1); at its first look after that
# it is caught at once if it still flies and is FIRST_MARGIN 1.5 m deep inside such a place; else, from its speed, the
# script works out where its flight comes down, and if that is
#   - within SPAWN_RADIUS 4.5 m of a soldier on a spawn point (3D, to the point 1 m up), or
#   - within FLAG_RADIUS 4.5 m of a flag's zone (3D, to its edge: the flag's radius + 1.2 + 0.3 m round the pole's foot;
#     inside it too; worked out for the pole foot's level and 2.5 m under it),
# it is sent under the map at once by the bus, whoever threw it, whichever side holds the flag, and everybody is told in
# the chat. Only one that then moves on down there counts as removed; one that stays put is a ghost (logged, nothing
# said). Nobody is punished. 4.5 m: one C4 killed every soldier with full health within 2 m, nearly every one within
# 3.5-4 m, now and then one at 4-4.5 m (140 =FL= Karkand rounds); its blast reaches 7 m.
# A C4 that landed in such a place uncaught has stuck: only logged (STUCK_TRY 1: the bus's ways tried anyway). One
# whose flight comes down within VEHICLE_NEAR 6 m of a vehicle with soldiers in it is left (thrown at a vehicle).
# The places: Strike at Karkand, Conquest 64 (the bus's data): the main base (Gas Station, its flag and 12 spawn points)
# left out (MAIN_BASES 0) - 8 flags and 36 spawn points.
#
# INSTALL
#   1. Copy this file and mm_flbus.py to <server folder>/admin/modules/
#   2. modmanager.con: the same line as for 1.x (modmanager.loadModule "mm_c4clear"); mm_flbus needs no line of its
#      own. Settings of 1.x for the ways to remove (mm_c4clear.AWAY_SIDE ...) are now mm_flbus.<NAME>.
#   3. Restart the server.
#   4. c4clear.log: "c4clear 2.0.0 loaded (...", at a Karkand round "round on strike_at_karkand (layout gpm_cq:64): 36
#      spawn points and 8 flags watched"; flbus.log: "c4clear joined".
#
# Settings: modmanager.con, mm_c4clear.<NAME> (the ways to remove are the bus's: mm_flbus.<NAME>).
#
# History
# 2.0.0 (2026-11-08) On the bus (mm_flbus 1.0.0); the C4 rule as 1.1.3. AWAY_SIDE, REMOVE_DEPTH and the other ways'
#   settings are now the bus's (mm_flbus.AWAY_SIDE ...); C4_SEEN is the bus's list of names.
# 1.1.3 vehicles from the players' crews (not every PlayerControlObject: mm_noarmor_v2); the template from the start.
# 1.1.2 none touched before 0.05 s; 1.1.1 first-look catch, looks every 0.03 s; 1.1.0 caught in the air; 1.0.0
#   removed after lying still 0.3 s (ghosts: a stuck C4 cannot be moved).

__version__ = 2.0

__required_modules__ = {
	'modmanager': 1.0,
	'mm_flbus': 1.0
}

__supports_reload__ = False

__supported_games__ = {
	'bf2': True,
	'bf2142': False,
	'bfheroes': False,
	'bfp4f': False
}

__description__ = 'C4Clear v2.0.0 (ModManager module, on mm_flbus)'

import mm_flbus as BUS

VERSION = '2.0.0'

# ------------------------------------------------------------------ settings
MAPS = 'strike_at_karkand'   # the maps watched, by the game's map name, comma-separated ('all': every map with data)
SPAWN_RADIUS = 4.5     # m: a C4 coming down this close to a soldier on a spawn point (the point 1 m up, 3D) is removed
FLAG_RADIUS = 4.5      # m: ... or this close to a flag's zone (3D, to its edge) - inside the zone too
EARLIEST = 0.05        # s: no C4 is moved before it is this old (moved at once, it stays where it is in the games)
FIRST_LOOK = 1         # 1: caught at its first look (after EARLIEST) when still flying FIRST_MARGIN deep inside a place
FIRST_MARGIN = 1.5     # m: how deep inside (spawn point: within 3 m; flag: 3 m from its zone or inside)
FLIGHT_MAX = 3.0       # s: a C4 is caught only while it flies in its first this many seconds (later: it rides a vehicle)
C4_GRAVITY = 9.8       # m/s2: how fast a flying C4 falls faster (the log tells it for up to 10 C4 a round)
STUCK_TRY = 0          # 1: one that has landed (stuck) in a place is tried anyway with the bus's ways (for tests)
ZONE_EXTRA = 0.3       # m: a flag's zone: the flag's radius + 1.2 m + this (as claycap)
MAIN_BASES = 0         # 1: the main base's flag and spawn points (Gas Station) count too
VEHICLE_NEAR = 6.0     # m: a C4 whose flight comes down this close to a vehicle with soldiers in it is left (0: no check)
REST_TIME = 0.3        # s: a C4 lying still this long in a place uncaught is logged as stuck
CHECK_EVERY = 0.03     # s: how often the C4 are looked at (a thrown C4 flies some 0.15-1.2 s)
SAY = 1                # 1: tell everybody in the chat
MSG_SPAWN = '[C4Clear] C4 near a spawn point at %s has been removed.'   # %s: the point's flag
MSG_FLAG = '[C4Clear] C4 at the flag %s has been removed.'              # %s: the flag
TEST_CHAT = 0          # 1: say in the chat what was found for EVERY C4 and each way tried (for a test)
LOG_FILE = 'c4clear.log'   # in the server folder; '' - no log

SOLDIER_UP = 1.0       # m: a soldier's position over the ground he stands on
ZONE_FOOT = 1.2        # m: added to a flag's radius (as claycap)
ZONE_LOW = 2.5         # m: a flight is also worked out down to this far under a flag pole's foot

dist3 = BUS.dist3
F = None

S = {'points': None, 'zones': None, 'built': 0, 'idle': 0, 'left': [], 'tally': {}, 'ways': {}, 'stuck': {},
     'ghosts': 0, 'veh_left': 0, 'gone_later': [], 'parents': 0, 'falls': 0}

def log(text):
    if F is not None:
        F.log(text)
    else:
        BUS.write_log(LOG_FILE, text)

def test_say(text):
    if F is not None:
        F.test_say(text)

def mapname():
    return BUS.S['map']


# ------------------------------------------------------------------ the places' tests
def place_hit(pos):
    # ('spawn', point, m to the soldier on it) of the nearest spawn point within SPAWN_RADIUS; else ('flag', zone, m to
    # its edge - below 0: inside) of the nearest flag zone within FLAG_RADIUS; or None
    best = None
    for p in S['points'] or []:
        d = dist3(pos, p['x'], p['h'], p['z'])
        if d <= SPAWN_RADIUS and (best is None or d < best[2]):
            best = ('spawn', p, d)
    if best is not None:
        return best
    for zn in S['zones'] or []:
        d = dist3(pos, zn['x'], zn['h'], zn['z']) - zn['R']
        if d <= FLAG_RADIUS and (best is None or d < best[2]):
            best = ('flag', zn, d)
    return best

def nearest_places(pos):
    # (point, m, zone, m to its edge) the nearest of each (for TEST_CHAT)
    bp = bz = None
    for p in S['points'] or []:
        d = dist3(pos, p['x'], p['h'], p['z'])
        if bp is None or d < bp[1]:
            bp = (p, d)
    for zn in S['zones'] or []:
        d = dist3(pos, zn['x'], zn['h'], zn['z']) - zn['R']
        if bz is None or d < bz[1]:
            bz = (zn, d)
    return bp, bz

def comes_down(pos, v, gh):
    # (the point, s) where a C4 at pos flying at v comes down to the height gh (C4_GRAVITY), or None (not within 2 s)
    vy = v[1]
    dy = pos[1] - gh
    if C4_GRAVITY > 0.1:
        disc = vy * vy + 2.0 * C4_GRAVITY * dy
        if disc < 0:
            return None
        s = (vy + disc ** 0.5) / C4_GRAVITY
    else:
        if vy >= -0.01:
            return None
        s = dy / -vy
    if s < 0 or s > 2.0:
        return None
    return (pos[0] + v[0] * s, gh, pos[2] + v[2] * s), s

def catch_hit(pos, v):
    # (kind, place, m, the point it comes down at, s) of the place its flight comes down by: on a spawn point's ground
    # within SPAWN_RADIUS of a soldier on it, or at a flag pole's foot level (or ZONE_LOW under it) within FLAG_RADIUS of
    # its zone; or None
    best = None
    for p in S['points'] or []:
        if abs(p['x'] - pos[0]) + abs(p['z'] - pos[2]) > 40.0:
            continue
        cd = comes_down(pos, v, p['h'] - SOLDIER_UP)
        if cd is None:
            continue
        d = dist3(cd[0], p['x'], p['h'], p['z'])
        if d <= SPAWN_RADIUS and (best is None or d < best[2]):
            best = ('spawn', p, d, cd[0], cd[1])
    if best is not None:
        return best
    for zn in S['zones'] or []:
        if abs(zn['x'] - pos[0]) + abs(zn['z'] - pos[2]) > 60.0:
            continue
        for gh in (zn['h'], zn['h'] - ZONE_LOW):
            cd = comes_down(pos, v, gh)
            if cd is None:
                continue
            d = dist3(cd[0], zn['x'], zn['h'], zn['z']) - zn['R']
            if d <= FLAG_RADIUS and (best is None or d < best[2]):
                best = ('flag', zn, d, cd[0], cd[1])
    return best

def first_hit(pos):
    # at a C4's first look (it has just left the thrower's hand): (kind, place, m, pos, 0) of a place it is already
    # FIRST_MARGIN deep inside the reach of - within SPAWN_RADIUS - FIRST_MARGIN of a soldier on a spawn point, or
    # FLAG_RADIUS - FIRST_MARGIN of a flag zone (or inside it); or None
    best = None
    for p in S['points'] or []:
        d = dist3(pos, p['x'], p['h'], p['z'])
        if d <= SPAWN_RADIUS - FIRST_MARGIN and (best is None or d < best[2]):
            best = ('spawn', p, d, pos, 0.0)
    if best is not None:
        return best
    for zn in S['zones'] or []:
        d = dist3(pos, zn['x'], zn['h'], zn['z']) - zn['R']
        if d <= FLAG_RADIUS - FIRST_MARGIN and (best is None or d < best[2]):
            best = ('flag', zn, d, pos, 0.0)
    return best

def place_text(kind, pl, d):
    if kind == 'spawn':
        return 'near the spawn point %s (%s): %.1f m from a soldier on it' % (pl['name'], pl['flag'], d)
    if d <= 0:
        return 'at the flag %s: in its zone (%.1f m inside its edge)' % (pl['name'], -d)
    return 'at the flag %s: %.1f m from its zone' % (pl['name'], d)


# ------------------------------------------------------------------ the places this round
def places_ready(t):
    if S['built']:
        return S['points'] is not None
    L = BUS.layout(t)
    if L is None:
        return 0
    S['built'] = 1
    if L['key'] is None:
        S['points'], S['zones'], S['idle'] = [], [], 1
        log('round on %s: no data for this layout (the game shows %d flags) - idle this round' % (mapname(),
            L['game_flags']))
        return 1
    flag, main = {}, {}
    zones = []
    for cid, name, x, h, z, r, mn in L['flags']:
        flag[cid] = name
        main[cid] = mn
        if mn and not MAIN_BASES:
            continue
        zones.append({'name': name, 'x': x, 'h': h, 'z': z, 'r': r, 'R': r + ZONE_FOOT + ZONE_EXTRA})
    pts = []
    left = {}
    for name, cid, x, h, z in L['points']:
        fl = flag.get(cid, '?')
        if main.get(cid) and not MAIN_BASES:
            left[fl] = left.get(fl, 0) + 1
            continue
        pts.append({'name': name, 'flag': fl, 'x': x, 'h': h + SOLDIER_UP, 'z': z})
    S['points'], S['zones'] = pts, zones
    per = []
    n = {}
    for p in pts:
        if p['flag'] not in n:
            n[p['flag']] = 0
            per.append(p['flag'])
        n[p['flag']] = n[p['flag']] + 1
    parts = []
    for fl in per:
        parts.append('%s %d' % (fl, n[fl]))
    zz = []
    for zn in zones:
        zz.append('%s %.0f+%.1f m' % (zn['name'], zn['r'], ZONE_FOOT + ZONE_EXTRA))
    lo = []
    for fl in left.keys():
        lo.append('%s (main base: its flag and %d spawn points)' % (fl, left[fl]))
    log('round on %s (layout %s): %d spawn points and %d flags watched - spawn points: %s; flag zones: %s%s; a C4 '
        'coming down within %.1f m of a soldier on a point or %.1f m of a zone is removed' % (mapname(), L['key'],
        len(pts), len(zones), ', '.join(parts) or '-', ', '.join(zz) or '-', (lo and '; left out: ' + ', '.join(lo))
        or '', SPAWN_RADIUS, FLAG_RADIUS))
    if not pts and not zones:
        S['idle'] = 1
    return 1


# ------------------------------------------------------------------ what was found
def speed(r, t):
    # its speed now: from its first look while it flies (steadier), C4_GRAVITY allowed for; else the bus's
    if r['vel'] is None:
        return None
    d0 = t - r['t0']
    pf = r['p_first']
    pos = r['pos']
    if 0.02 <= d0 <= 1.0 and pf[1] > BUS.BELOW_MAP and pos[1] > BUS.BELOW_MAP:
        return ((pos[0] - pf[0]) / d0, (pos[1] - pf[1]) / d0 - 0.5 * C4_GRAVITY * d0, (pos[2] - pf[2]) / d0)
    return r['vel']

def tally_of(flag):
    tl = S['tally'].get(flag)
    if tl is None:
        tl = [0, 0, 0, {}]
        S['tally'][flag] = tl
    return tl

def found(r, x, pos, hit, t, first=0):
    # a C4 caught in the air: hit = (kind, place, m, the point it comes down at, s); first: at its first look
    kind, pl, d, q, s = hit
    x['kind'] = kind
    if kind == 'spawn':
        x['flag'], x['point'] = pl['flag'], pl['name']
    else:
        x['flag'], x['point'] = pl['name'], 'zone'
    x['where'] = place_text(kind, pl, d)
    tl = tally_of(x['flag'])
    tl[0] = tl[0] + 1
    tl[3][x['point']] = tl[3].get(x['point'], 0) + 1
    v = x['vel'] or (0.0, 0.0, 0.0)
    sp = (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) ** 0.5
    if first:
        log('%s: C4 %s caught at its first look from %.2f s on (%.2f s after it appeared), at (%.2f, %.2f, %.2f): %s - '
            'removing' % (mapname(), r['id'], EARLIEST, t - r['t0'], pos[0], pos[1], pos[2], x['where']))
    else:
        log('%s: C4 %s caught in the air, %.2f s after it appeared, at (%.2f, %.2f, %.2f), flying %.1f m/s - it would '
            'come down at (%.2f, %.2f, %.2f) in %.2f s: %s - removing' % (mapname(), r['id'], t - r['t0'], pos[0],
            pos[1], pos[2], sp, q[0], q[1], q[2], s, x['where']))
    test_say('C4 %s caught: %s - removing' % (r['id'], x['where']))
    BUS.remove(F, r, t, x['where'])

def tell(r, x):
    if x.get('told'):
        return
    x['told'] = 1
    if SAY:
        msg = MSG_FLAG
        if x['kind'] == 'spawn':
            msg = MSG_SPAWN
        BUS.say(BUS.fmt(msg, (x['flag'],)))

def on_removed(r, how, t):
    x = r['x'].get('c4clear')
    if x is None:
        return
    tl = tally_of(x['flag'])
    tl[1] = tl[1] + 1
    if r['rm']['sky_ok']:
        tl[2] = tl[2] - 1        # (counted as sent to the sky till now)
    S['ways'][how] = S['ways'].get(how, 0) + 1
    tell(r, x)

def on_sky(r, t):
    x = r['x'].get('c4clear')
    if x is None:
        return
    tl = tally_of(x['flag'])
    tl[2] = tl[2] + 1
    tell(r, x)

def on_ghost(r, t):
    S['ghosts'] = S['ghosts'] + 1

def on_gone(r, t):
    rm = r['rm']
    if rm is not None and rm['by'] is F and rm['done'] and not rm['ghost']:
        S['gone_later'].append(t - rm['done_t'])
        log('C4 %s (%s): gone from the game %.1f s after it was removed (it went off down there, or the game deleted '
            'it)' % (r['id'], rm['what'], t - rm['done_t']))

def stuck(r, x, pos, hit, t):
    # a C4 that has landed in a place uncaught: it has stuck there; logged (STUCK_TRY 1: the ways tried anyway)
    kind, pl, d = hit
    where = place_text(kind, pl, d)
    if STUCK_TRY:
        log('%s: C4 %s has landed and stuck %s, at (%.2f, %.2f, %.2f) - STUCK_TRY 1: tried anyway' % (mapname(), r['id'],
            where, pos[0], pos[1], pos[2]))
        x['vel'] = (0.0, 0.0, 0.0)
        found(r, x, pos, (kind, pl, d, pos, 0.0), t)
        return
    fl = pl.get('flag') or pl['name']
    S['stuck'][fl] = S['stuck'].get(fl, 0) + 1
    pred = ''
    if x['pred_from'] is not None:
        cd = comes_down(x['pred_from'][0], x['pred_from'][1], pos[1])
        if cd is not None:
            q = cd[0]
            pred = '; its flight was worked out to come down at (%.2f, %.2f, %.2f), %.1f m from where it did' % (q[0],
                q[1], q[2], ((q[0] - pos[0]) ** 2 + (q[2] - pos[2]) ** 2) ** 0.5)
    log('%s: C4 %s has landed %s, at (%.2f, %.2f, %.2f) [%.2f s after it appeared] - not caught in the air: it has '
        'stuck there and a script cannot remove a stuck C4 (moved, it would stay there as a ghost that still goes off) '
        '- left, nothing said%s' % (mapname(), r['id'], where, pos[0], pos[1], pos[2], t - r['t0'], pred))
    test_say('C4 %s has stuck %s - cannot be removed' % (r['id'], where))

def fall_note(r, x):
    # the first C4s of a round that flew uncaught: how fast they fell faster over their flight (to check C4_GRAVITY)
    tr = r['track']
    if S['falls'] >= 10 or x['acc_noted'] or len(tr) < 4:
        return
    x['acc_noted'] = 1
    p1, p2, p3 = tr[0], tr[int((len(tr) - 2) / 2)], tr[-2]
    if p3[0] - p1[0] < 0.15 or p2[0] - p1[0] < 0.05 or p3[0] - p2[0] < 0.05:
        return
    S['falls'] = S['falls'] + 1
    g = -2.0 * ((p3[1] - p2[1]) / (p3[0] - p2[0]) - (p2[1] - p1[1]) / (p2[0] - p1[0])) / (p3[0] - p1[0])
    log('C4 %s flew %.2f s (%d looks): it fell faster by %.1f m/s each second (C4_GRAVITY %.1f)' % (r['id'],
        p3[0] - p1[0], len(tr), g, C4_GRAVITY))

def on_vehicle(r, pos, t):
    # (how, the vehicle's template, m) if a C4 that lies still has stuck to a vehicle (its parent object is one) or lies
    # within VEHICLE_NEAR of one with soldiers in it; else None (for the log)
    par = BUS.parent_of(r['o'])
    if S['parents'] < 5:
        S['parents'] = S['parents'] + 1
        what = 'none'
        if par is not None:
            what = '%s (its root: %s)' % (BUS.tpl_name(par), BUS.tpl_name(BUS.root_of(par)))
        log('C4 %s: its parent object: %s' % (r['id'], what))
    if par is not None:
        rt = BUS.root_of(par)
        k = BUS.obj_key(rt)
        if (k is None or k not in BUS.soldier_keys(t)) and BUS.is_vehicle(BUS.tpl_name(rt)):
            return 'stuck to it (its parent object)', BUS.tpl_name(rt), 0.0
    if VEHICLE_NEAR > 0:
        v = BUS.vehicle_near(pos, VEHICLE_NEAR, t)
        if v is not None:
            return 'within %.0f m of it' % VEHICLE_NEAR, v[0], v[1]
    return None

# ------------------------------------------------------------------ the look
def new_x():
    return {'judged': None, 'fresh': 1, 'air_skip': 0, 'veh_noted': 0, 'pred_from': None, 'acc_noted': 0, 'kind': None,
            'flag': None, 'point': None, 'where': '', 'vel': None, 'told': 0}

def look(t):
    if S['idle']:
        return
    ready = places_ready(t)
    for r in BUS.track('c4', t):
        if not r['upd']:
            continue
        x = r['x'].get('c4clear')
        if x is None:
            x = new_x()
            r['x']['c4clear'] = x
        moved = r['moved']
        if moved:
            x['vel'] = speed(r, t)
        if r['rm'] is not None:
            continue                      # (being removed: the bus follows it)
        pos = r['pos']
        if pos[1] < BUS.BELOW_MAP:
            continue
        # nothing done before it is EARLIEST old (moved in its first moment, it stays where it is in the players' games)
        if t - r['t0'] < EARLIEST:
            continue
        # its first look after that: caught at once if it still flies and is deep inside a place's reach
        if x['fresh']:
            x['fresh'] = 0
            if ready and FIRST_LOOK and moved:
                hit = first_hit(pos)
                if hit is not None and (VEHICLE_NEAR <= 0 or BUS.vehicle_near(pos, VEHICLE_NEAR, t) is None):
                    x['vel'] = (0.0, 0.0, 0.0)
                    found(r, x, pos, hit, t, 1)
                    continue
        # in the air (it moved since the last look, in its first FLIGHT_MAX s): caught now if its flight comes down by a
        # spawn point or a flag - once it has landed it has stuck
        if moved and ready and x['vel'] is not None and t - r['t0'] <= FLIGHT_MAX and not x['air_skip']:
            x['pred_from'] = (pos, x['vel'])
            hit = catch_hit(pos, x['vel'])
            if hit is None:
                continue
            vn = None
            if VEHICLE_NEAR > 0:
                vn = BUS.vehicle_near(hit[3], VEHICLE_NEAR, t)
            if vn is None:
                found(r, x, pos, hit, t)
            else:
                x['air_skip'] = 1
                x['veh_noted'] = 1
                S['veh_left'] = S['veh_left'] + 1
                log('%s: C4 %s in the air %s - but it comes down %.1f m from a vehicle (%s): left' % (mapname(), r['id'],
                    place_text(hit[0], hit[1], hit[2]), vn[1], vn[0]))
                test_say('C4 %s: thrown at a vehicle (%s) - left' % (r['id'], vn[0]))
            continue
        # judged once it has lain still REST_TIME (again if it moves and comes to rest again: the bus keeps when it
        # last moved, whoever looked then)
        if not ready or x['judged'] == r['still'] or t - r['still'] < REST_TIME:
            continue
        x['judged'] = r['still']
        fall_note(r, x)
        hit = place_hit(pos)
        if hit is not None and not x['air_skip']:
            v = on_vehicle(r, pos, t)
            if v is None:
                stuck(r, x, pos, hit, t)
            elif not x['veh_noted']:
                x['veh_noted'] = 1
                S['veh_left'] = S['veh_left'] + 1
                log('%s: C4 %s %s, at (%.2f, %.2f, %.2f) - left: on a vehicle (%s, %s, %.1f m)' % (mapname(), r['id'],
                    place_text(hit[0], hit[1], hit[2]), pos[0], pos[1], pos[2], v[1], v[0], v[2]))
                test_say('C4 %s: on a vehicle (%s, %s) - left' % (r['id'], v[1], v[0]))
        elif F is not None and F.test_chat:
            bp, bz = nearest_places(pos)
            where = []
            if bp is not None:
                where.append('nearest spawn point %s (%s): %.1f m' % (bp[0]['name'], bp[0]['flag'], bp[1]))
            if bz is not None:
                where.append('nearest flag zone %s: %.1f m' % (bz[0]['name'], bz[1]))
            test_say('C4 %s at %.1f %.1f %.1f: not near a spawn point or flag (%s)' % (r['id'], pos[0], pos[2], pos[1],
                '; '.join(where) or 'nothing watched'))

# ------------------------------------------------------------------ rounds
def round_start(t):
    S['points'], S['zones'], S['built'], S['idle'] = None, None, 0, 0
    S['tally'], S['ways'], S['stuck'] = {}, {}, {}
    S['ghosts'], S['veh_left'], S['gone_later'], S['parents'], S['falls'] = 0, 0, [], 0, 0
    places_ready(t)

def round_end(t):
    if S['idle']:
        log('round summary on %s: idle (nothing watched)' % mapname())
        return
    L = []
    n = rr = k = 0
    for name in S['tally'].keys():
        tl = S['tally'][name]
        n, rr, k = n + tl[0], rr + tl[1], k + tl[2]
        L.append((-tl[0], name))
    L.sort()
    parts = []
    for z, name in L:
        tl = S['tally'][name]
        pts = list(tl[3].keys())
        pts.sort()
        pp = []
        for q in pts:
            pp.append('%s %d' % (q, tl[3][q]))
        parts.append('%s %d (%s; removed %d)' % (name, tl[0], ', '.join(pp), tl[1]))
    ways = []
    for w in S['ways'].keys():
        ways.append('%s %d' % (w, S['ways'][w]))
    ways.sort()
    vl = ''
    if S['gone_later']:
        vl = vl + '; %d of the removed later gone from the game (%.0f-%.0f s after)' % (len(S['gone_later']),
            min(S['gone_later']), max(S['gone_later']))
    if S['ghosts']:
        vl = vl + '; %d of them ghosts (they had stuck)' % S['ghosts']
    st = list(S['stuck'].keys())
    if st:
        st.sort()
        ss = []
        m = 0
        for fl in st:
            ss.append('%s %d' % (fl, S['stuck'][fl]))
            m = m + S['stuck'][fl]
        vl = vl + '; %d more landed in places uncaught and stuck there (%s)' % (m, ', '.join(ss))
    if S['veh_left']:
        vl = vl + '; %d more left for vehicles' % S['veh_left']
    seen = BUS.seen_n('c4')
    if n:
        log('round summary on %s: %d C4 seen, %d caught in the air by spawn points or flags - %s; removed %d (%s), only '
            'sent to the sky %d, not removed %d%s' % (mapname(), seen, n, '; '.join(parts), rr, ', '.join(ways) or '-',
            k, n - rr - k, vl))
    else:
        log('round summary on %s: %d C4 seen, none caught by a spawn point or flag%s' % (mapname(), seen, vl))
    if F is not None:
        log(F.load_line(t))


def c4clear_init():
    global F
    F = BUS.feature('c4clear', 'C4', LOG_FILE, 'C4Clear')
    F.log_file = LOG_FILE
    F.maps = MAPS
    F.every = CHECK_EVERY
    F.look = look
    F.round_start = round_start
    F.round_end = round_end
    F.on_removed = on_removed
    F.on_sky = on_sky
    F.on_ghost = on_ghost
    F.on_gone = on_gone
    F.test_chat = TEST_CHAT
    extra = ''
    if MAIN_BASES:
        extra = extra + '; main bases too'
    else:
        extra = extra + '; main bases left out'
    if VEHICLE_NEAR > 0:
        extra = extra + '; one coming down within %.0f m of a vehicle with soldiers in it left alone' % VEHICLE_NEAR
    extra = extra + '; none touched before %.2f s old' % EARLIEST
    if FIRST_LOOK:
        extra = extra + '; caught at its first look after that when still flying %.1f m deep inside' % FIRST_MARGIN
    if STUCK_TRY:
        extra = extra + '; STUCK_TRY 1: one that has stuck in a place tried anyway'
    if not SAY:
        extra = extra + '; nothing said in the chat'
    if TEST_CHAT:
        extra = extra + '; TEST_CHAT is on'
    log('c4clear %s loaded, on mm_flbus %s (maps: %s; a C4 caught in the air, looked at every %.2f s, when its flight '
        'comes down within %.1f m of a soldier on a spawn point or %.1f m of a flag zone (its radius + %.1f m)%s; '
        'removed by the bus: see flbus.log; nobody punished)' % (VERSION, BUS.VERSION, MAPS, CHECK_EVERY, SPAWN_RADIUS,
        FLAG_RADIUS, ZONE_FOOT + ZONE_EXTRA, extra))
    BUS.add(F)


# ------------------------------------------------------------------ ModManager interface
# The defaults are the values of the settings above. modmanager.con can override them: mm_c4clear.<NAME> <value>
configDefaults = {}
for _k in ['MAPS', 'SPAWN_RADIUS', 'FLAG_RADIUS', 'EARLIEST', 'FIRST_LOOK', 'FIRST_MARGIN', 'FLIGHT_MAX', 'C4_GRAVITY',
           'STUCK_TRY', 'ZONE_EXTRA', 'MAIN_BASES', 'VEHICLE_NEAR', 'REST_TIME', 'CHECK_EVERY', 'SAY', 'MSG_SPAWN',
           'MSG_FLAG', 'TEST_CHAT', 'LOG_FILE']:
    configDefaults[_k] = globals()[_k]

class C4Clear( object ):

    def __init__( self, modManager ):
        self.mm = modManager
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
        c4clear_init()
        try:
            self.mm.info( 'c4clear %s is running on mm_flbus (see %s)' % ( VERSION, LOG_FILE or 'no log' ) )
        except:
            pass

    def shutdown( self ):
        self.__state = 2
        if F is not None:
            F.active = 0
            F.look = None

    def update( self ):
        pass

def mm_load( modManager ):
    return C4Clear( modManager )

