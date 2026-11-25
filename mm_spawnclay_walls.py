# mm_spawnclay_walls.py - SpawnClay Walls 1.0.2: claymores aimed at a soldiers' spawn point are removed - unless a
# wall stands between the claymore and the whole spawn point - on a Battlefield 2 server, as a Multiplay ModManager
# module on the =FL= bus mm_flbus (ModManager 1.0 or later, Python 2.3 of BF2 1.5)
#
# What it does: every 0.1 s it looks at every claymore. One that has lain still 0.3 s and whose trigger fan comes within
# SPAWN_RADIUS 1 m of a spawn point, on the point's level (LEVEL_DIFF 2.5 m higher or lower at most), would be removed
# by spawnclay 2.0 - whoever placed it, whichever side holds the point's flag. The trigger fan (the object files:
# triggerRadius 7, triggerAngle 30) is where an enemy sets it off: TRIGGER_RADIUS 8 m out (the 10.11 test: up to ~8 m),
# 30 degrees each side of the way it faces - the claymore's own yaw from the game (0 north, 90 east, clockwise).
#
# The walls (new; Sagara 09.11: "walls protect both from setting a claymore off and from its blast; a tree trunk may
# stop the setting off, but not the blast"; 10.11: the blast cone, straight away, spawnclay and claycap both):
#   such a claymore is LEFT when every line from its charge to the spawn point's zone inside its blast cone passes
#   through a wall:
#     - the zone: the point itself and two rings round it, at SPAWN_RADIUS / 2 and SPAWN_RADIUS (16 points each);
#     - the blast cone: BLAST_ANGLE 45 degrees each side of its face, BLAST_REACH 8 m (where it kills); a ring point
#       outside the cone does not count (if none is inside: the one nearest the claymore);
#     - each line: from CHARGE_UP 0.15 and 0.4 m over the claymore to BODY_UP 0.3, 0.9 and 1.5 m over the point's
#       ground (a soldier lying, crouching, standing); and LOW_LINES (1.0.2): from LOW_UP 0.05 and 0.1 m over it to
#       LOW_BODY 0.05 and 0.1 m over the ground - a slot under a wall (11.11: the container by warehouse_1);
#     - the walls: mm_flwalls - the faces of the placed objects' collision meshes (as BF2 Round Replay draws them),
#       without the materials bullets go through (glass, thin metal, wood ...), without objects under 1.2 m across;
#       trees are not in it, so a tree never shields - as for the blast. NOT_WALLS (1.0.2): objects that are never a
#       wall - the containers, bins and train wagons (room under them);
#   One clear line is enough to remove it. The lines are tried a few at a time (WALL_MS 5 ms of a look), the likeliest
#   first; a check not finished in WALL_GIVE_UP 20 s counts as clear. A claymore whose face cannot be read: its blast
#   taken as a full circle. WALLS 0: no walls (as spawnclay 2.0.0).
#   Everybody is told in the chat only of a removed claymore; one left is in the log (and TEST_CHAT).
#
# The spawn points are the bus's (from the level's GamePlayObjects.con): Strike at Karkand, Conquest 64 - 48 points at
# 9 flags. The main base's 12 (Gas Station) are left out (MAIN_BASES 0): 36 points watched. On another layout (16, 32)
# or map the module stays idle; mm_flwalls has walls for Karkand only (elsewhere every line counts as clear).
#
# The bus asks the game for the claymores (once for every script), keeps one record of each, and removes the ones
# spawnclay_walls finds: down, lift + down, cut, sky - each checked, written in spawnclay_walls.log (the ways' settings
# are mm_flbus.<NAME>).
#
# Next to mm_claycap_walls: a claymore that claycap_walls removes itself (lying in a flag's zone; or its fan reaches
# into one and it is not walled off from the zone) is left to it (LEAVE_TO_CLAYCAP 1), so that it is removed once and
# said once in the chat; one that claycap_walls leaves (walled off from the flag's zone) is judged here by the spawn
# points. If claycap has not taken it CLAYCAP_WAIT 5 s later, it is removed here. Next to the old mm_claycap 2.0 it
# works as spawnclay 2.0.0 did.
#
# INSTALL (instead of mm_spawnclay - never both)
#   1. Copy this file and mm_flwalls.py (1.0.2 or later) to <server folder>/admin/modules/; mm_flbus.py (1.0.1 or
#      later) must be there too.
#   2. modmanager.con: replace the line modmanager.loadModule "mm_spawnclay" with
#      modmanager.loadModule "mm_spawnclay_walls"; settings are mm_spawnclay_walls.<NAME> (rename the old
#      mm_spawnclay.<NAME> lines). mm_flwalls and mm_flbus need no line.
#   3. Restart the server (it cannot be reloaded with "mm reloadModule").
#   4. spawnclay_walls.log (server folder) should contain "spawnclay_walls 1.0.0 loaded, on mm_flbus ... walls:
#      strike_at_karkand: 30148 faces ...", and at the start of a Karkand round "round on strike_at_karkand (layout
#      gpm_cq:64): 36 spawn points watched"; flbus.log "spawnclay_walls joined".
#   If mm_spawnclay is loaded as well, spawnclay_walls stays idle and says so in its log.
#
# Settings: the values in the settings block below are the defaults; a line in modmanager.con overrides one, e.g.
#   mm_spawnclay_walls.SPAWN_RADIUS 3.0   mm_spawnclay_walls.WALLS 1   mm_spawnclay_walls.TEST_CHAT 0
#
# The log: "loaded", "round on" (the spawn points watched), one line for each claymore aimed at a spawn point - the
# point, its flag, how close the trigger comes, its facing, where, and what the walls gave: "removing (a clear line
# ...)" or "LEFT: walled off ... (the objects in the way)"; a line for each way tried and what came of it,
# "REMOVED (...)", and at the end of every round a summary (by flag and point, the ones left by the walls) and the load.
#
# History
# 1.0.2 (2026-11-12) The containers, bins and train wagons are no wall (NOT_WALLS), and low lines (LOW_LINES 1,
#   0.05/0.1 m to 0.05/0.1 m over the ground). The 11.11 test at warehouse_1: claymores walled off by the container
#   went off on Sagara on the point - three did him no harm, the next three killed him ("his OWN claymore"); Sagara
#   12.11: "under it there are three holes, through which the claymore reacts" - claymores in it and behind it are to
#   be removed. In mm_flwalls the container's floor is only beams and its sides have slots 0-0.10 m high: the lines at
#   0.15 m and up passed over them. In 140 =FL= replayed rounds no claymore was left by those objects; the low lines
#   remove 2 more (claycap). FIRST_LINES 10 (was 6): the 4 low lines to the point itself come with the first ones.
#   Needs mm_flwalls 1.0.2. claytest can ask walls_job(lines) for the same check.
# 1.0.1 (2026-11-10) The 10.11 test at warehouse_1 (40 claymores at once by the containers): walls checks did not
#   finish in 3 s (then 20 s) and walled claymores were removed as clear, and claymores with a clear first line
#   waited up to 20 s behind long checks. Now: mm_flwalls 1.0.1 (the faces that blocked the last lines first:
#   about 20 times fewer faces looked at there); every new check gets its FIRST_LINES 6 lines at once; WALL_MS 5
#   (was 3), WALL_GIVE_UP 20 s (was 3; Sagara set 20 on the test server). The rules are the same. The test also
#   showed: a claymore behind a container went off 4 m from Sagara on the point and did him no harm; three behind
#   the high wall at trainaccident_3 (5-7 m, aimed) did not go off; without a wall one kills at up to ~8 m
#   (TRIGGER_RADIUS 8, BLAST_REACH 8 set on the test server).
# 1.0.0 (2026-11-10) spawnclay 2.0.0 + the walls (Sagara 10.11: no log-only stage, act at once; the blast cone; both
#   spawnclay and claycap). 140 =FL= Karkand rounds replayed through the real code, with claycap_walls 1.0.0 next to
#   it, against spawnclay 2.0.0 + claycap 2.0.0: SPAWN_RADIUS 1 m - 47 more claymores left (5 kills), 38 of them at
#   Hotel; 3 m - 180 more left (42 kills), 170 at Hotel - on the terrace round the flag, 2.4 m over hotel_1, behind its
#   edge (house_high_04). None of the people those claymores killed was on a spawn point or in a flag's zone: 35 were
#   on the Hotel terrace, going up to the flag (not a spawn point: it is the zone's edge, outside claycap's 6.5 m).

__version__ = 1.02

__required_modules__ = {
	'modmanager': 1.0,
	'mm_flbus': 1.01,
	'mm_flwalls': 1.02
}

__supports_reload__ = False

__supported_games__ = {
	'bf2': True,
	'bf2142': False,
	'bfheroes': False,
	'bfp4f': False
}

__description__ = 'SpawnClay Walls v1.0.2 (ModManager module, on mm_flbus, walls from mm_flwalls)'

import bf2
import host
import sys
import mm_flbus as BUS
import mm_flwalls as WALLS_MOD

VERSION = '1.0.2'
NAME = 'spawnclay_walls'

# ------------------------------------------------------------------ settings
MAPS = 'strike_at_karkand'   # the maps watched, by the game's map name, comma-separated ('all': every map with data)
SPAWN_RADIUS = 2.0     # m: a claymore is judged when its trigger fan comes this close to a spawn point (on the map)
LEVEL_DIFF = 2.5       # m: ... and it lies at most this much higher or lower than the point (the same floor)
MAIN_BASES = 0         # 1: the main base's spawn points (Gas Station) count too (mm_flwalls has no walls there)
TRIGGER_RADIUS = 8.0   # m: how far out its trigger reaches (object files: triggerRadius 7; the 10.11 test: up to ~8 m)
TRIGGER_ANGLE = 30.0   # degrees each side of its face (object files: triggerAngle 30)
FACE_OFFSET = 0.0      # degrees added to the claymore's yaw (getRotation) to get the way it faces
FACE_MIRROR = 0        # 1: the yaw counted the other way round (if a test shows east and west swapped)
UNKNOWN_FACE = 1       # 1: a claymore whose yaw cannot be read: its trigger taken as a full circle
                       #    (0: only one lying within SPAWN_RADIUS of a point)
WALLS = 1              # 1: a claymore walled off from the whole spawn zone inside its blast cone is left; 0: no walls
BLAST_ANGLE = 45.0     # degrees each side of its face: its blast cone
BLAST_REACH = 8.0      # m: how far its blast kills (on the map; 10.11: killed from full health at 7.9 m; 1.0.0: 7.5)
CHARGE_UP = '0.15 0.4'       # m over the claymore: where the lines start
BODY_UP = '0.3 0.9 1.5'      # m over the spawn point's ground: where they end (lying, crouching, standing)
RING_POINTS = 16       # points on each of the two rings round a spawn point
NOT_WALLS = ('container_cargo_red container_op_blue container_cl_green_trash container_cl_red_trash '
             'trash_dumpster train_cargowag_01 train_cargowag_02 train_cargowag_03 train_engine fueltankwagon')
                       # objects that are never a wall (1.0.2; Sagara 12.11: holes under the container by warehouse_1 -
                       # a claymore in it killed him on the point; bins and train wagons have room under them too)
LOW_LINES = 1          # 1: also lines near the ground (1.0.2: a slot under a wall, as under that container)
LOW_UP = '0.05 0.1'    # m over the claymore: where the low lines start
LOW_BODY = '0.05 0.1'  # m over the ground at the other end: where they end
WALL_MS = 5.0          # ms of line tests at most in one look (the rest in the next looks; 1.0.0: 3)
FIRST_LINES = 10       # the first lines of every new check (to the point itself: 6 + 4 low ones) are tried
                       # before the rest (1.0.1: 6)
FIRST_MS = 10.0        # ms for those first lines in one look at most (one check at least)
WALL_GIVE_UP = 20.0    # s: a walls check not finished in this long counts as a clear line (removed; 1.0.0: 3)
LINE_SKIP = 0.03       # the part of each line at either end not looked at (the claymore's own surface, the ground)
LEAVE_TO_CLAYCAP = 1   # 1: a claymore that mm_claycap_walls (or mm_claycap) removes itself is left to it
CLAYCAP_WAIT = 5.0     # s: ... unless claycap has not taken it this long after
REST_TIME = 0.3        # s: a claymore is judged once it has lain still this long (it is thrown up to ~6 m)
CHECK_EVERY = 0.1      # s: how often the claymores are looked at
SAY = 1                # 1: tell everybody in the chat (a removed claymore only)
MSG_REMOVED = '[SpawnClay] A claymore aimed at a spawn point at %s has been removed.'   # %s: the point's flag
TEST_CHAT = 0          # 1: say in the chat what was found for EVERY claymore and each way tried (for a test)
LOG_FILE = 'spawnclay_walls.log'   # in the server folder; '' - no log

# ------------------------------------------------------------------ log, chat
F = None

def log(text):
    if F is not None:
        F.log(text)
    else:
        BUS.write_log(LOG_FILE, text)

def err_text():
    return BUS.err_text()

def say(text):
    BUS.say(text)

def test_say(text):
    if TEST_CHAT:
        say('[SpawnClay test] ' + text)

def fmt(msg, args):
    return BUS.fmt(msg, args)

def now():
    return BUS.now()

def obj_key(o):
    return BUS.obj_key(o)

# ------------------------------------------------------------------ state
S = {'map': None, 'warned': {}, 'spawns': None, 'round_t': 0.0, 'layout': None, 'left': [], 'tally': {}, 'ways': {},
     'idle': 0, 'cc_left': 0, 'game_flags': 0, 'jobs': [], 'left_n': 0, 'walls0': (0, 0)}

# ------------------------------------------------------------------ the spawn points this round (the bus's)
def spawns_ready(t):
    if S['spawns'] is not None:
        return 1
    lay = BUS.layout(t)
    if lay is None:
        if t - S['round_t'] > 60 and not S['warned'].get('noflags'):
            S['warned']['noflags'] = 1
            log('round on %s: the game shows no flags - the layout cannot be told, nothing watched yet' % S['map'])
        return 0
    S['game_flags'] = lay['game_flags']
    if lay['key'] is None:
        S['spawns'] = []
        S['idle'] = 1
        log('round on %s: no spawn data for this layout (the game shows %d flags; the bus knows: %s) - idle this '
            'round' % (S['map'], S['game_flags'], BUS.known_layouts(S['map']) or 'nothing for this map'))
        return 1
    S['layout'] = lay['key']
    flag, main = {}, {}
    for f in lay['flags']:
        flag[f[0]] = f[1]
        main[f[0]] = f[6]
    pts = []
    left = {}
    S['left'] = []
    for name, cid, x, h, z in lay['points']:
        fl = flag.get(cid, '?')
        if main.get(cid) and not MAIN_BASES:
            left[fl] = left.get(fl, 0) + 1
            continue
        pts.append({'name': name, 'flag': fl, 'x': x, 'h': h, 'z': z})
    for fl in left.keys():
        S['left'].append('%s (main base, %d points)' % (fl, left[fl]))
    S['spawns'] = pts
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
    log('round on %s (layout %s): %d spawn points watched (%s)%s' % (S['map'], S['layout'], len(pts),
        ', '.join(parts) or '-', (S['left'] and '; left out: ' + ', '.join(S['left'])) or ''))
    if not pts:
        S['idle'] = 1
    return 1

# (no math module needed: BF2's Python may not have it)
PI = 3.14159265358979

def sin_cos(deg):
    # (sin, cos) of an angle in degrees
    x = deg % 360.0
    if x > 180.0:
        x = x - 360.0
    sign = 1.0
    if x > 90.0:
        x, sign = 180.0 - x, -1.0          # sin(180 - x) = sin x, cos(180 - x) = -cos x
    elif x < -90.0:
        x, sign = -180.0 - x, -1.0
    r = x * PI / 180.0
    r2 = r * r
    s = r * (1.0 - r2 / 6.0 * (1.0 - r2 / 20.0 * (1.0 - r2 / 42.0 * (1.0 - r2 / 72.0 * (1.0 - r2 / 110.0)))))
    c = 1.0 - r2 / 2.0 * (1.0 - r2 / 12.0 * (1.0 - r2 / 30.0 * (1.0 - r2 / 56.0 * (1.0 - r2 / 90.0))))
    return s, c * sign

def face_of(o):
    # the way a claymore faces, degrees (0 north, clockwise - the game's yaw), or None
    try:
        r = o.getRotation()
        yaw = float(r[0])
    except:
        return None
    if FACE_MIRROR:
        yaw = -yaw
    return (yaw + FACE_OFFSET) % 360.0

COMPASS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']

def compass(deg):
    return COMPASS[int((deg % 360.0) / 22.5 + 0.5) % 16]

def bearing_ok(vx, vz, fx, fz, d, ch):
    # 1 if the direction (vx, vz) (length d) is within the fan's angle round (fx, fz)
    return vx * fx + vz * fz >= d * ch

def seg_dist(px, pz, ax, az, bx, bz):
    dx, dz = bx - ax, bz - az
    L = dx * dx + dz * dz
    u = 0.0
    if L > 0:
        u = ((px - ax) * dx + (pz - az) * dz) / L
        if u < 0.0:
            u = 0.0
        elif u > 1.0:
            u = 1.0
    qx, qz = ax + u * dx - px, az + u * dz - pz
    return (qx * qx + qz * qz) ** 0.5

def fan_gap(px, pz, x, z, face):
    # m on the map from (px, pz) to the trigger fan of a claymore at (x, z) facing face (None: a full circle)
    vx, vz = px - x, pz - z
    d = (vx * vx + vz * vz) ** 0.5
    if face is None:
        return max(0.0, d - TRIGGER_RADIUS)
    if d < 1e-6:
        return 0.0
    fx, fz = sin_cos(face)
    sh, ch = sin_cos(TRIGGER_ANGLE)
    if bearing_ok(vx, vz, fx, fz, d, ch):
        return max(0.0, d - TRIGGER_RADIUS)
    best = None
    for ex, ez in ((fx * ch + fz * sh, fz * ch - fx * sh), (fx * ch - fz * sh, fz * ch + fx * sh)):
        g = seg_dist(px, pz, x, z, x + TRIGGER_RADIUS * ex, z + TRIGGER_RADIUS * ez)
        if best is None or g < best:
            best = g
    return best


def spawn_hits(pos, face):
    # [(point, m from its trigger to the point on the map, m from the claymore to the point)] of the spawn points on
    # the claymore's level that its trigger comes within SPAWN_RADIUS of, nearest first
    plain = face is None and not UNKNOWN_FACE
    reach = TRIGGER_RADIUS + SPAWN_RADIUS
    if plain:
        reach = SPAWN_RADIUS
    out = []
    for p in S['spawns'] or []:
        if abs(pos[1] - p['h']) > LEVEL_DIFF:
            continue
        dx, dz = p['x'] - pos[0], p['z'] - pos[2]
        d2 = dx * dx + dz * dz
        if d2 > reach * reach:
            continue
        d = d2 ** 0.5
        if plain:
            g = d
        else:
            g = fan_gap(p['x'], p['z'], pos[0], pos[2], face)
        if g > SPAWN_RADIUS:
            continue
        out.append((g, d, p['name'], p))
    out.sort()
    L = []
    for g, d, nm, p in out:
        L.append((p, g, d))
    return L

def nearest_spawn(pos, face):
    # (point, m from its trigger, m from the claymore, m the claymore lies higher) of the spawn point its trigger comes
    # nearest to, those on its level first (for TEST_CHAT)
    best = None
    for p in S['spawns'] or []:
        g = fan_gap(p['x'], p['z'], pos[0], pos[2], face)
        dh = pos[1] - p['h']
        k = g
        if abs(dh) > LEVEL_DIFF:
            k = g + 10000.0
        if best is None or k < best[0]:
            d = ((p['x'] - pos[0]) ** 2 + (p['z'] - pos[2]) ** 2) ** 0.5
            best = (k, (p, g, d, dh))
    if best is None:
        return None
    return best[1]

def level_text(dh):
    if dh > -0.05 and dh < 0.05:
        return 'on its level'
    if dh >= 0:
        return '%.1f m higher' % dh
    return '%.1f m lower' % -dh

# ------------------------------------------------------------------ the walls (mm_flwalls)
def numbers(text, default):
    L = []
    try:
        for w in str(text).replace(',', ' ').split():
            L.append(float(w))
    except:
        L = []
    if not L:
        L = default
    return L

def walls_on():
    return WALLS and WALLS_MOD.has_map(S['map'])

def not_walls():
    # {face: 1} of the NOT_WALLS objects on this map (1.0.2), or None
    try:
        return WALLS_MOD.skip_of(S['map'], NOT_WALLS)
    except:
        return None

def walls_job(lines):
    # the walls check of a set of lines, NOT_WALLS taken as no wall (claytest asks this too)
    return WALLS_MOD.Lines(S['map'], lines, LINE_SKIP, 1.0 - LINE_SKIP, not_walls())

def low_pairs():
    # the (over the claymore, over the ground) heights of the low lines (1.0.2), or []
    if not LOW_LINES:
        return []
    L = []
    for u in numbers(LOW_UP, [0.05, 0.1]):
        for b in numbers(LOW_BODY, [0.05, 0.1]):
            L.append((u, b))
    return L

def walls_setup_text():
    # the walls' settings for the loaded line
    t = 'lines from %s m over it to %s m over the ground' % ('/'.join(['%g' % v for v in numbers(CHARGE_UP, [0.15, 0.4])]),
        '/'.join(['%g' % v for v in numbers(BODY_UP, [0.3, 0.9, 1.5])]))
    if LOW_LINES:
        t = t + ', low lines from %s to %s m' % ('/'.join(['%g' % v for v in numbers(LOW_UP, [0.05, 0.1])]),
            '/'.join(['%g' % v for v in numbers(LOW_BODY, [0.05, 0.1])]))
    t = t + '; never a wall (NOT_WALLS): ' + WALLS_MOD.skip_text('strike_at_karkand', NOT_WALLS)
    return t

def in_cone(x, z, sx, sz, face, fc):
    # 1 if (sx, sz) is inside the blast cone of a claymore at (x, z) facing face; fc = (sin, cos) of face, cos of the
    # cone's half angle
    vx, vz = sx - x, sz - z
    d = (vx * vx + vz * vz) ** 0.5
    if d > BLAST_REACH:
        return 0
    if face is None or d < 1e-6:
        return 1
    return vx * fc[0] + vz * fc[1] >= d * fc[2]

def zone_lines(pos, face, hits):
    # the lines to try for a claymore at pos facing face, aimed at the points hits: [(ax, ah, az, bx, bh, bz, what)]
    ups = numbers(CHARGE_UP, [0.15, 0.4])
    bodies = numbers(BODY_UP, [0.3, 0.9, 1.5])
    lows = low_pairs()
    fc = None
    if face is not None:
        fx, fz = sin_cos(face)
        sh, ch = sin_cos(BLAST_ANGLE)
        fc = (fx, fz, ch)
    n = int(RING_POINTS)
    rings = []
    if SPAWN_RADIUS > 0 and n > 0:
        for k in range(n):
            rings.append(sin_cos(k * 360.0 / n))
    lines = []
    for p, g, d in hits:
        S0 = [(p['x'], p['z'], 0.0)]
        for r in (SPAWN_RADIUS / 2.0, SPAWN_RADIUS):
            if r <= 0:
                continue
            for s, c in rings:
                S0.append((p['x'] + r * s, p['z'] + r * c, r))
        T = []
        for sx, sz, r in S0:
            if in_cone(pos[0], pos[2], sx, sz, face, fc):
                dd = ((sx - pos[0]) ** 2 + (sz - pos[2]) ** 2) ** 0.5
                T.append((r > 0, dd, sx, sz, r))
        if not T:
            best = None
            for sx, sz, r in S0:
                dd = ((sx - pos[0]) ** 2 + (sz - pos[2]) ** 2) ** 0.5
                if best is None or dd < best[1]:
                    best = (1, dd, sx, sz, r)
            T = [best]
        T.sort()             # (the point itself first, then the ring points nearest the claymore)
        for ring, dd, sx, sz, r in T:
            for b in (bodies[len(bodies) // 2:] + bodies[:len(bodies) // 2]):
                for u in ups:
                    lines.append((pos[0], pos[1] + u, pos[2], sx, p['h'] + b, sz, (p['name'], r, u, b)))
            for u, b in lows:
                lines.append((pos[0], pos[1] + u, pos[2], sx, p['h'] + b, sz, (p['name'], r, u, b)))
    return lines

def line_text(L):
    nm, r, u, b = L[6]
    if r > 0:
        where = '%s (%.1f m from it)' % (nm, r)
    else:
        where = nm
    return 'from %.2f m over it to %.2f m over %s' % (u, b, where)

def run_walls(t):
    # the claymores waiting for their walls check, WALL_MS of lines in all: first each check that has tried fewer than
    # FIRST_LINES lines gets them (those to the point itself: a claymore with a clear line is found at once even while
    # long checks run - 1.0.1; FIRST_MS for all of them at most, one at least), then the oldest checks go on
    if not S['jobs']:
        return
    a = BUS.clock()
    until = a + WALL_MS / 1000.0
    first_until = a + FIRST_MS / 1000.0
    live = []
    for r in S['jobs']:
        x = r['x'].get(NAME)
        if x is None or x['job'] is None:
            continue
        if r['rm'] is not None or x['judged'] != r['still']:
            x['job'] = None          # (being removed by another script, or it moved: judged again)
            continue
        live.append(r)
    ran = 0
    for r in live:
        x = r['x'][NAME]
        job = x['job']
        if job.result is None and job.i < FIRST_LINES and t - x['job_t'] < WALL_GIVE_UP:
            if ran and BUS.clock() >= first_until:
                break
            ran = 1
            job.run(BUS.clock, first_until + 1.0, int(FIRST_LINES) - job.i)
    keep = []
    first = 1
    for r in live:
        x = r['x'][NAME]
        res = x['job'].result
        if res is None:
            if t - x['job_t'] >= WALL_GIVE_UP:
                res = ('late', None, x['job'].i)
            elif first or BUS.clock() < until:
                first = 0
                res = x['job'].run(BUS.clock, until)      # (at least one line: the oldest check each look goes on)
        if res is None:
            keep.append(r)
            continue
        job = x['job']
        x['job'] = None
        ms = job.spent * 1000.0
        if res[0] == 'walled':
            left_by_walls(r, x, res, ms, len(job.lines))
        else:
            if res[0] == 'clear':
                why = 'not walled off: a clear line %s (line %d of %d, %.1f ms)' % (line_text(res[1]), res[2],
                      len(job.lines), ms)
            else:
                why = 'the walls check did not finish in %.0f s (%d of %d lines, all blocked so far) - taken as clear' % (
                      WALL_GIVE_UP, res[2], len(job.lines))
            decided(r, x, t, why)
    S['jobs'] = keep

def left_by_walls(r, x, res, ms, n):
    pos = r['pos']
    p, g, d = x['hits'][0]
    names = []
    for q, gg, dd in x['hits']:
        names.append(q['name'])
    tl = tally_of(p['flag'])
    tl[4] = tl[4] + 1
    tl[5][p['name']] = tl[5].get(p['name'], 0) + 1
    S['left_n'] = S['left_n'] + 1
    log('%s: claymore %s aimed at the spawn point%s %s (%s): %s comes %.1f m from the point; it lies %.1f m from it, %s, '
        'at (%.2f, %.2f, %.2f) [%.2f s after it appeared] - LEFT: walled off from the spawn zone inside its blast cone '
        '(%.0f deg each side, %.1f m): all %d lines blocked (%s) [%.1f ms]' % (S['map'], r['id'],
        (len(names) > 1 and 's') or '', ', '.join(names), p['flag'], trigger_text(x['face']), g, d,
        level_text(pos[1] - p['h']), pos[0], pos[1], pos[2], x['t_judged'] - r['t0'], BLAST_ANGLE, BLAST_REACH, n,
        WALLS_MOD.walls_text(res[1]), ms))
    test_say('claymore %s aimed at %s (%s), %.1f m short - LEFT: behind %s (%d lines)' % (r['id'], ', '.join(names),
        p['flag'], g, WALLS_MOD.walls_text(res[1], 2), n))

# ------------------------------------------------------------------ mm_claycap_walls / mm_claycap next to it (on the bus too)
def find_mod(name):
    m = sys.modules.get(name)
    if m is not None:
        return m
    for k in sys.modules.keys():
        if k[-(len(name) + 1):] == '.' + name and sys.modules[k] is not None:
            return sys.modules[k]
    return None

def claycap_mod():
    # (module, 1 if it is claycap_walls) of the claycap on the bus, or (None, 0)
    m = find_mod('mm_claycap_walls')
    if m is not None:
        f = getattr(m, 'F', None)
        if f is not None and f.active and not getattr(m, 'S', {}).get('idle'):
            return m, 1
    m = find_mod('mm_claycap')
    if m is not None:
        return m, 0
    return None, 0

def claycap_note(e):
    if e not in S['warned']:
        S['warned'][e] = 1
        log('claycap could not be asked: ' + e)

def claycap_acted(r):
    # 1 if a claycap is removing this claymore (the record says who removes it)
    rm = r['rm']
    return rm is not None and rm['by'].name in ('claycap', 'claycap_walls')

def claycap_takes(r, pos, face):
    # what claycap does with this claymore: (flag, 'takes') - it removes it; (flag, 'wait') - claycap_walls has not
    # finished with it yet; None - claycap leaves it (not in a zone, or walled off from the zone), or no claycap
    if not LEAVE_TO_CLAYCAP:
        return None
    m, walls = claycap_mod()
    if m is None:
        return None
    try:
        f = getattr(m, 'F', None)
        if f is None or not f.active or not m.S.get('zones'):
            return None
        hit = m.zone_at(pos)
        if hit is not None:
            return (hit[0]['name'], 'takes')
        if not getattr(m, 'FAN_RULE', 0):
            return None
        fc = m.face_of(r['o'])
        if fc is None and not m.UNKNOWN_FACE:
            return None
        hit = m.fan_hit(pos, fc)
        if hit is None:
            return None
        if not walls:
            return (hit[0]['name'], 'takes')
        xc = r['x'].get('claycap_walls')
        if xc is not None and xc.get('v_still') == r['still']:
            if xc.get('verdict') == 'remove':
                return (hit[0]['name'], 'takes')
            if xc.get('verdict') == 'left':
                return None
        return (hit[0]['name'], 'wait')
    except:
        claycap_note(err_text())
    return None

# ------------------------------------------------------------------ what was found
def face_text(face):
    if face is None:
        return 'facing unknown'
    return 'facing %.0f deg (%s)' % (face, compass(face))

def trigger_text(face):
    if face is None:
        if UNKNOWN_FACE:
            return 'its trigger (%s: a %.0f m circle)' % (face_text(face), TRIGGER_RADIUS)
        return 'it (facing unknown)'
    return 'its trigger fan (%.0f m, %.0f deg each side, %s)' % (TRIGGER_RADIUS, TRIGGER_ANGLE, face_text(face))

def tally_of(flag):
    tl = S['tally'].get(flag)
    if tl is None:
        tl = [0, 0, 0, {}, 0, {}]      # found, removed, only sent to the sky, by point, left by the walls, by point
        S['tally'][flag] = tl
    return tl

def found(r, x, pos, sp, t, face, why=''):
    p, g, d = sp
    x['flag'] = p['flag']
    x['point'] = p['name']
    tl = tally_of(p['flag'])
    tl[0] = tl[0] + 1
    tl[3][p['name']] = tl[3].get(p['name'], 0) + 1
    what = trigger_text(face)
    if g <= 0.0:
        how = 'the point is inside %s' % what
    else:
        how = '%s comes %.1f m from the point' % (what, g)
    if why:
        why = '; ' + why
    log('%s: claymore %s aimed at the spawn point %s (%s): %s; it lies %.1f m from the point, %s, at (%.2f, %.2f, '
        '%.2f) [%.2f s after it appeared]%s - removing' % (S['map'], r['id'], p['name'], p['flag'], how, d,
        level_text(pos[1] - p['h']), pos[0], pos[1], pos[2], t - r['t0'], why))
    test_say('claymore %s at %.1f %.1f %.1f, %s: aimed at the spawn point %s (%s), %.1f m short - removing' % (
        r['id'], pos[0], pos[2], pos[1], face_text(face), p['name'], p['flag'], g))
    BUS.remove(F, r, t, 'aimed at the spawn point %s (%s)' % (p['name'], p['flag']))

def tell(x):
    if x['told']:
        return
    x['told'] = 1
    if SAY:
        say(fmt(MSG_REMOVED, (x['flag'],)))

def on_removed(r, how, t):
    x = r['x'].get(NAME)
    if x is None or x['flag'] is None:
        return
    tl = tally_of(x['flag'])
    tl[1] = tl[1] + 1
    if r['rm']['sky_ok']:
        tl[2] = tl[2] - 1        # (counted as sent to the sky till now)
    S['ways'][how] = S['ways'].get(how, 0) + 1
    tell(x)

def on_sky(r, t):
    x = r['x'].get(NAME)
    if x is None or x['flag'] is None:
        return
    tl = tally_of(x['flag'])
    tl[2] = tl[2] + 1
    tell(x)

# ------------------------------------------------------------------ the look every CHECK_EVERY s
def new_x():
    return {'judged': None, 'flag': None, 'point': None, 'told': 0, 'cc': None, 'cc_t': 0.0, 'cc_done': 0,
            'cc_hit': None, 'cc_face': None, 'cc_still': None, 'job': None, 'job_t': 0.0, 'hits': None, 'face': None,
            'why': '', 't_judged': 0.0}

def decided(r, x, t, why):
    # the walls (if any) let it be removed: to claycap, or removed here
    pos = r['pos']
    face = x['face']
    sp = x['hits'][0]
    x['why'] = why
    cc = claycap_takes(r, pos, face)
    if cc is None:
        found(r, x, pos, sp, t, face, why)
        return
    fl, how = cc
    p = sp[0]
    x['cc'], x['cc_t'], x['cc_hit'], x['cc_face'], x['cc_still'] = fl, t, sp, face, r['still']
    S['cc_left'] = S['cc_left'] + 1
    log('%s: claymore %s aimed at the spawn point %s (%s), %s, %.1f m short, at (%.2f, %.2f, %.2f)%s - left to claycap '
        '(flag %s%s)' % (S['map'], r['id'], p['name'], p['flag'], face_text(face), sp[1], pos[0], pos[1], pos[2],
        (why and '; ' + why) or '', fl, (how == 'wait' and ': its walls check is not finished yet') or ''))
    test_say('claymore %s aimed at the spawn point %s (%s) - left to claycap (flag %s)' % (r['id'], p['name'],
        p['flag'], fl))

def look(t):
    if S['idle']:
        return
    ready = spawns_ready(t)
    for r in BUS.track('claymore', t):
        if not r['upd']:
            continue
        x = r['x'].get(NAME)
        if x is None:
            x = new_x()
            r['x'][NAME] = x
        if r['rm'] is not None:
            continue                      # (being removed - by spawnclay_walls or by claycap: the bus follows it)
        pos = r['pos']
        if pos[1] < BUS.BELOW_MAP:
            continue
        if x['cc'] is not None and x['cc_still'] != r['still']:
            x['cc'], x['cc_done'] = None, 0   # (it moved: judged again)
        if x['cc'] is not None:
            # left to claycap: removed here if claycap_walls leaves it after all, or has not taken it CLAYCAP_WAIT s later
            if not x['cc_done']:
                if claycap_acted(r):
                    continue
                cc = claycap_takes(r, pos, x['cc_face'])
                if cc is None:
                    x['cc_done'] = 1
                    S['cc_left'] = S['cc_left'] - 1
                    found(r, x, pos, x['cc_hit'], t, x['cc_face'], (x['why'] and x['why'] + '; ' or '') +
                          'claycap leaves it (walled off from the flag\'s zone)')
                elif t - x['cc_t'] >= CLAYCAP_WAIT:
                    x['cc_done'] = 1
                    S['cc_left'] = S['cc_left'] - 1
                    found(r, x, pos, x['cc_hit'], t, x['cc_face'], (x['why'] and x['why'] + '; ' or '') +
                          'claycap has not taken it in %.0f s' % CLAYCAP_WAIT)
            continue
        if x['job'] is not None:
            continue                      # (its walls check goes on in run_walls)
        # judged once it has lain still REST_TIME (again if it moves and comes to rest again)
        if not ready or x['judged'] == r['still'] or t - r['still'] < REST_TIME:
            continue
        x['judged'] = r['still']
        x['t_judged'] = t
        face = face_of(r['o'])
        hits = spawn_hits(pos, face)
        if hits:
            x['hits'], x['face'] = hits, face
            if walls_on():
                x['job'] = walls_job(zone_lines(pos, face, hits))
                x['job_t'] = t
                S['jobs'].append(r)
            else:
                decided(r, x, t, '')
        elif TEST_CHAT:
            ns = nearest_spawn(pos, face)
            where = 'no spawn point watched'
            if ns is not None:
                p, g, d, dh = ns
                where = 'nearest: %s (%s) - its trigger stays %.1f m short of it; it lies %.1f m from it, %s' % (
                    p['name'], p['flag'], g, d, level_text(dh))
            test_say('claymore %s at %.1f %.1f %.1f, %s: not aimed at a spawn point (%s)' % (r['id'], pos[0], pos[2],
                pos[1], face_text(face), where))
    run_walls(t)

# ------------------------------------------------------------------ rounds
def other_loaded():
    # the old mm_spawnclay is loaded too: this one stays idle (the claymores would be judged twice)
    m = find_mod('mm_spawnclay')
    return m is not None

def round_start(t):
    S['map'] = BUS.S['map']
    S['spawns'] = None
    S['layout'] = None
    S['left'] = []
    S['round_t'] = t
    S['idle'] = 0
    S['cc_left'] = 0
    S['left_n'] = 0
    S['jobs'] = []
    S['game_flags'] = 0
    S['tally'] = {}
    S['ways'] = {}
    S['walls0'] = (WALLS_MOD.STATS['lines'], WALLS_MOD.STATS['faces'])
    if 'noflags' in S['warned']:
        del S['warned']['noflags']
    if other_loaded():
        S['idle'] = 1
        log('round on %s: mm_spawnclay is loaded as well - spawnclay_walls stays idle (load only one of the two)' %
            S['map'])
        return
    if WALLS and not WALLS_MOD.has_map(S['map']):
        log('round on %s: mm_flwalls has no walls for this map - every claymore aimed at a spawn point is removed, as '
            'without walls' % S['map'])
    not_walls()              # (made now, not in the first check)
    spawns_ready(t)

def round_end(t):
    if S['idle']:
        log('round summary on %s: idle (no spawn point watched)' % S['map'])
        S['tally'] = {}
        S['ways'] = {}
        return
    L = []
    n = r = k = w = 0
    for name in S['tally'].keys():
        tl = S['tally'][name]
        n, r, k, w = n + tl[0], r + tl[1], k + tl[2], w + tl[4]
        L.append((-(tl[0] + tl[4]), name))
    L.sort()
    parts = []
    lefts = []
    for z, name in L:
        tl = S['tally'][name]
        if tl[0]:
            pts = list(tl[3].keys())
            pts.sort()
            pp = []
            for q in pts:
                pp.append('%s %d' % (q, tl[3][q]))
            parts.append('%s %d (%s; removed %d)' % (name, tl[0], ', '.join(pp), tl[1]))
        if tl[4]:
            pts = list(tl[5].keys())
            pts.sort()
            pp = []
            for q in pts:
                pp.append('%s %d' % (q, tl[5][q]))
            lefts.append('%s %d (%s)' % (name, tl[4], ', '.join(pp)))
    ways = []
    for wy in S['ways'].keys():
        ways.append('%s %d' % (wy, S['ways'][wy]))
    ways.sort()
    cc = ''
    if S['cc_left']:
        cc = '; %d more left to claycap' % S['cc_left']
    lw = ''
    if w:
        lw = '; left by the walls: %d - %s' % (w, '; '.join(lefts))
    seen = BUS.seen_n('claymore')
    if n:
        log('round summary on %s: %d claymores seen, %d aimed at spawn points and removed by the rule - %s; removed %d '
            '(%s), only sent to the sky %d, not removed %d%s%s' % (S['map'], seen, n, '; '.join(parts), r,
            ', '.join(ways) or '-', k, n - r - k, cc, lw))
    else:
        log('round summary on %s: %d claymores seen, none removed%s%s' % (S['map'], seen, cc, lw))
    l0, f0 = S.get('walls0') or (0, 0)
    nl = WALLS_MOD.STATS['lines'] - l0
    if nl:
        log('walls this round: %d lines tried (%d faces looked at, %.0f per line) - all scripts using mm_flwalls' % (nl,
            WALLS_MOD.STATS['faces'] - f0, (WALLS_MOD.STATS['faces'] - f0) / float(nl)))
    S['tally'] = {}
    S['ways'] = {}
    if F is not None:
        log(F.load_line(t))

# ------------------------------------------------------------------ start
def spawnclay_init():
    global F
    F = BUS.feature(NAME, 'Claymore', LOG_FILE, 'SpawnClay')
    F.log_file = LOG_FILE
    F.maps = MAPS
    F.every = CHECK_EVERY
    F.look = look
    F.round_start = round_start
    F.round_end = round_end
    F.on_removed = on_removed
    F.on_sky = on_sky
    F.ghost_check = 0            # (a claymore sent under the map is removed: claycap's test 07.11)
    F.test_chat = TEST_CHAT
    extra = ''
    if UNKNOWN_FACE:
        extra = '; a %.0f m circle if its face is unknown' % TRIGGER_RADIUS
    if FACE_OFFSET or FACE_MIRROR:
        extra = extra + '; face: yaw%s + %.0f deg' % ((FACE_MIRROR and ' mirrored') or '', FACE_OFFSET)
    if MAIN_BASES:
        extra = extra + '; main bases too'
    else:
        extra = extra + '; main bases left out'
    if WALLS:
        extra = extra + ('; LEFT if walled off from the whole spawn zone (the point and rings at %.1f and %.1f m) inside '
            'its blast cone (%.0f deg each side, %.1f m): %s; %.0f ms a look; walls: mm_flwalls %s, %s' % (
            SPAWN_RADIUS / 2.0, SPAWN_RADIUS, BLAST_ANGLE, BLAST_REACH, walls_setup_text(), WALL_MS, WALLS_MOD.VERSION,
            WALLS_MOD.map_text('strike_at_karkand')))
    else:
        extra = extra + '; WALLS 0: walls not taken into account'
    if LEAVE_TO_CLAYCAP:
        extra = extra + '; one that claycap removes is left to it'
    if not SAY:
        extra = extra + '; nothing said in the chat'
    if TEST_CHAT:
        extra = extra + '; TEST_CHAT is on'
    log('spawnclay_walls %s loaded, on mm_flbus %s (maps: %s; a claymore whose trigger fan (%.0f m, %.0f deg each side) '
        'comes within %.1f m of a spawn point, %.1f m higher or lower at most%s; removed by the bus: down, lift + down, '
        'cut, sky - see flbus.log; nobody punished)' % (VERSION, BUS.VERSION, MAPS, TRIGGER_RADIUS, TRIGGER_ANGLE,
        SPAWN_RADIUS, LEVEL_DIFF, extra))
    BUS.add(F)


# ------------------------------------------------------------------ ModManager interface
# The defaults are the values of the settings above. modmanager.con can override them: mm_spawnclay_walls.<NAME> <value>
configDefaults = {}
for _k in ['MAPS', 'SPAWN_RADIUS', 'LEVEL_DIFF', 'MAIN_BASES', 'TRIGGER_RADIUS', 'TRIGGER_ANGLE', 'FACE_OFFSET',
           'FACE_MIRROR', 'UNKNOWN_FACE', 'WALLS', 'BLAST_ANGLE', 'BLAST_REACH', 'CHARGE_UP', 'BODY_UP', 'RING_POINTS',
           'NOT_WALLS', 'LOW_LINES', 'LOW_UP', 'LOW_BODY',
           'WALL_MS', 'FIRST_LINES', 'FIRST_MS', 'WALL_GIVE_UP', 'LINE_SKIP', 'LEAVE_TO_CLAYCAP', 'CLAYCAP_WAIT', 'REST_TIME', 'CHECK_EVERY', 'SAY',
           'MSG_REMOVED', 'TEST_CHAT', 'LOG_FILE']:
    configDefaults[_k] = globals()[_k]

class SpawnClayWalls( object ):

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
        spawnclay_init()
        try:
            self.mm.info( 'spawnclay_walls %s is running on mm_flbus (see %s)' % ( VERSION, LOG_FILE or 'no log' ) )
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
    return SpawnClayWalls( modManager )
