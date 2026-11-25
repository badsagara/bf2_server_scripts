# mm_claycap_walls.py - ClayCap Walls 1.0.2: claymores inside a flag's capture zone are removed, and those whose
# trigger fan reaches into one - unless a wall stands between the claymore and the whole zone - on a Battlefield 2
# server, as a Multiplay ModManager module on the =FL= bus mm_flbus (ModManager 1.0 or later, Python 2.3 of BF2 1.5)
#
# What it does: every 0.1 s it looks at every claymore, once it has lain still 0.3 s (main bases left out; whoever
# placed it and whichever side owns the flag):
#   - lying inside a flag's capture zone: removed, walls or not (as claycap 2.0);
#   - its trigger fan reaches into a zone (the object files: triggerRadius 7, triggerAngle 30; TRIGGER_RADIUS 8 m out -
#     the 10.11 test - 30 degrees each side of the way it faces, the claymore's own yaw from the game): removed -
#     unless every line from its charge to the part of the zone inside its blast cone passes through a wall; then it
#     is LEFT (new):
#       - the zone's part: points every SAMPLE_ANGLE 10 degrees and SAMPLE_STEP 1 m out from the claymore inside its
#         blast cone (BLAST_ANGLE 45 degrees each side of its face, BLAST_REACH 8 m) that lie in the zone, on the
#         claymore's level (as the fan rule: a soldier standing there); if none: the zone's point nearest to it;
#       - each line: from CHARGE_UP 0.15 and 0.4 m over the claymore to BODY_UP 0.3, 0.9 and 1.5 m over its ground;
#         and LOW_LINES (1.0.2): from LOW_UP 0.05 and 0.1 m over it to LOW_BODY 0.05 and 0.1 m over the ground (a slot
#         under a wall);
#       - the walls: mm_flwalls - the faces of the placed objects' collision meshes, without the materials bullets go
#         through and without objects under 1.2 m across; trees are not in it, so a tree never shields. NOT_WALLS
#         (1.0.2): objects that are never a wall - the containers, bins and train wagons (room under them).
#     One clear line is enough to remove it. A few lines each look (WALL_MS 5 ms), the likeliest first; a check not
#     finished in WALL_GIVE_UP 20 s counts as clear. Face unreadable: its blast taken as a full circle. WALLS 0: no
#     walls (as claycap 2.0.0).
# The zone is BF2 Round Replay's "Claymore at a flag", 0.3 m wider: a sphere of the flag's radius (from the level
# files) + 1.2 m + ZONE_EXTRA 0.3 m round the foot of the flag pole, in 3D - a claymore counts when a soldier standing
# where it lies (his position is 1 m over his feet) would be in it. Everybody is told in the chat of a removed claymore
# only; one left is in the log (and TEST_CHAT). Only the maps in MAPS are watched (Karkand by default); mm_flwalls has
# walls for Karkand's flags only (elsewhere every line counts as clear).
#
# The bus asks the game for the claymores (once for every script), keeps one record of each, and removes the ones
# claycap_walls finds - down, lift + down, cut, sky - each checked and written in claycap_walls.log (the ways'
# settings are mm_flbus.<NAME>). mm_spawnclay_walls leaves to it the claymores it removes itself, and reads what it
# found for one whose fan reaches a zone (removed, or left by the walls) - so that each is removed and said once.
#
# INSTALL (instead of mm_claycap - never both)
#   1. Copy this file and mm_flwalls.py (1.0.2 or later) to <server folder>/admin/modules/; mm_flbus.py (1.0.1 or
#      later) must be there too.
#   2. modmanager.con: replace the line modmanager.loadModule "mm_claycap" with modmanager.loadModule "mm_claycap_walls"
#      (before mm_spawnclay_walls); settings are mm_claycap_walls.<NAME> (rename the old mm_claycap.<NAME> lines).
#   3. Restart the server (it cannot be reloaded with "mm reloadModule").
#   4. claycap_walls.log (server folder) should contain "claycap_walls 1.0.0 loaded, on mm_flbus ... walls: ...";
#      flbus.log "claycap_walls joined".
#   If mm_claycap is loaded as well, claycap_walls stays idle and says so in its log.
#
# Settings: the values in the settings block below are the defaults; a line in modmanager.con overrides one, e.g.
#   mm_claycap_walls.ZONE_EXTRA 0.3   mm_claycap_walls.WALLS 1   mm_claycap_walls.TEST_CHAT 0
#
# The log: "loaded", "round on" (the flags watched), one line for each claymore found in a zone or reaching into one
# (the flag, how far from the pole, where, how long after it appeared, and for the fan what the walls gave), a line for
# each way tried and what came of it, "REMOVED (...)", and at the end of every round a summary and the load.
#
# History
# 1.0.2 (2026-11-12) The containers, bins and train wagons are no wall (NOT_WALLS), and low lines (LOW_LINES 1,
#   0.05/0.1 m to 0.05/0.1 m over the ground) - as spawnclay_walls 1.0.2: the 11.11 test at warehouse_1 (claymores
#   walled off by the container killed Sagara on the point) and Sagara 12.11 ("under it there are three holes";
#   claymores in it and behind it are to be removed). The Train Accident flag's zone comes within 1 m of a wagon.
#   FIRST_LINES 10 (was 6): the 4 low lines to the nearest zone point come with the first ones. Needs mm_flwalls
#   1.0.2.
# 1.0.1 (2026-11-10) The 10.11 test at warehouse_1 (40 claymores at once by the containers): walls checks did not
#   finish in 3 s (then 20 s) and walled claymores were removed as clear, and claymores with a clear first line
#   waited up to 20 s behind long checks. Now: mm_flwalls 1.0.1 (the faces that blocked the last lines first:
#   about 20 times fewer faces looked at there); every new check gets its FIRST_LINES 6 lines at once; WALL_MS 5
#   (was 3), WALL_GIVE_UP 20 s (was 3; Sagara set 20 on the test server). The rules are the same. The test also
#   showed: a claymore behind a container went off 4 m from Sagara on the point and did him no harm; three behind
#   the high wall at trainaccident_3 (5-7 m, aimed) did not go off; without a wall one kills at up to ~8 m
#   (TRIGGER_RADIUS 8, BLAST_REACH 8 set on the test server).
# 1.0.0 (2026-11-10) claycap 2.0.0 + the walls for the fan rule (Sagara 10.11: the blast cone; at once, no log-only
#   stage; spawnclay and claycap both). A claymore lying in a zone is removed as before. 140 =FL= Karkand rounds
#   replayed through the real code: of the 548 claymores claycap 2.0.0 removes, 26 are left (2 kills; Hotel 16, Square
#   5, Gatehouse 3) - none of whose victims was in a flag's zone or on a spawn point.

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

__description__ = 'ClayCap Walls v1.0.1 (ModManager module, on mm_flbus, walls from mm_flwalls)'

import bf2
import host
import sys
import mm_flbus as BUS
import mm_flwalls as WALLS_MOD

VERSION = '1.0.2'
NAME = 'claycap_walls'

# ------------------------------------------------------------------ settings
MAPS = 'strike_at_karkand'   # the maps watched, by the game's map name, comma-separated; 'all': every map
ZONE_EXTRA = 0.3       # m: added to every flag's zone (the site's zone is the flag's radius + 1.2 m)
MAIN_BASES = 0         # 1: the main bases' flags (that cannot be taken) count too (mm_flwalls has no walls there)
FAN_RULE = 1           # 1: also a claymore whose trigger fan reaches into a zone (0: only one lying in a zone)
TRIGGER_RADIUS = 8.0   # m: how far out its trigger reaches (object files: triggerRadius 7; the 10.11 test: up to ~8 m)
TRIGGER_ANGLE = 30.0   # degrees each side of its face (object files: triggerAngle 30)
FACE_OFFSET = 0.0      # degrees added to the claymore's yaw (getRotation) to get the way it faces
FACE_MIRROR = 0        # 1: the yaw counted the other way round (if a test shows east and west swapped)
UNKNOWN_FACE = 1       # 1: a claymore whose yaw cannot be read: its trigger taken as a full circle (0: zone only)
UNKNOWN_RADIUS = 10.0  # m: radius of a flag the script has no data for, when the game does not give one (0: not watched)
WALLS = 1              # 1: one whose fan reaches a zone, walled off from the zone inside its blast cone, is left
BLAST_ANGLE = 45.0     # degrees each side of its face: its blast cone
BLAST_REACH = 8.0      # m: how far its blast kills (on the map; 10.11: killed from full health at 7.9 m; 1.0.0: 7.5)
SAMPLE_ANGLE = 10.0    # degrees between the zone's points tried, out from the claymore
SAMPLE_STEP = 1.0      # m between them
CHARGE_UP = '0.15 0.4'       # m over the claymore: where the lines start
BODY_UP = '0.3 0.9 1.5'      # m over the claymore's ground: where they end (a soldier lying, crouching, standing)
WALL_MS = 5.0          # ms of line tests at most in one look (the rest in the next looks; 1.0.0: 3)
FIRST_LINES = 10       # the first lines of every new check (to the nearest zone point: 6 + 4 low ones) are tried
                       # before the rest (1.0.1: 6)
FIRST_MS = 10.0        # ms for those first lines in one look at most (one check at least)
WALL_GIVE_UP = 20.0    # s: a walls check not finished in this long counts as a clear line (removed; 1.0.0: 3)
LINE_SKIP = 0.03       # the part of each line at either end not looked at (the claymore's own surface, the ground)
NOT_WALLS = ('container_cargo_red container_op_blue container_cl_green_trash container_cl_red_trash '
             'trash_dumpster train_cargowag_01 train_cargowag_02 train_cargowag_03 train_engine fueltankwagon')
                       # objects that are never a wall (1.0.2; Sagara 12.11: holes under the container by warehouse_1 -
                       # a claymore in it killed him on the point; bins and train wagons have room under them too)
LOW_LINES = 1          # 1: also lines near the ground (1.0.2: a slot under a wall, as under that container)
LOW_UP = '0.05 0.1'    # m over the claymore: where the low lines start
LOW_BODY = '0.05 0.1'  # m over the ground at the other end: where they end
REST_TIME = 0.3        # s: a claymore is judged once it has lain still this long (it is thrown up to ~6 m)
CHECK_EVERY = 0.1      # s: how often the claymores are looked at
SAY = 1                # 1: tell everybody in the chat (a removed claymore only)
MSG_REMOVED = '[ClayCap] A claymore at the flag %s has been removed.'   # %s: the flag
TEST_CHAT = 0          # 1: say in the chat what was found for EVERY claymore and each way tried (for a test)
LOG_FILE = 'claycap_walls.log'   # in the server folder; '' - no log

# the rule (the site's zoneOf, v271)
ZONE_FOOT = 1.2        # m: the zone reaches this much further than the level's radius (measured on 42 demos)
SOLDIER_UP = 1.0       # m: a soldier's position is this far over his feet

CP_TYPE = 'dice.hfe.world.ObjectTemplate.ControlPoint'

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
        say('[ClayCap test] ' + text)

def fmt(msg, args):
    return BUS.fmt(msg, args)

def now():
    return BUS.now()

# ------------------------------------------------------------------ state
S = {'map': None, 'warned': {}, 'zones': None, 'round_t': 0.0, 'zone_try': -99.0, 'layout': None, 'left': [],
     'tally': {}, 'ways': {}, 'jobs': [], 'left_n': 0, 'idle': 0, 'walls0': (0, 0)}

# ------------------------------------------------------------------ the flags' zones this round
def near_entry(L, x, z):
    best, bd = None, 9.0          # (within 3 m on the map)
    for e in L:
        d = (e[1] - x) ** 2 + (e[2] - z) ** 2
        if d < bd:
            best, bd = e, d
    return best

def cp_param(cp, name):
    try:
        return cp.cp_getParam(name)
    except:
        return None

def cp_radius(cp):
    try:
        r = float(cp.getTemplateProperty('radius'))
        if r > 0:
            return r
    except:
        pass
    return None

def load_zones(mp):
    # -> [zone] (None: the game shows no flags yet); zone = {name, x, h, z (the centre), R (how far it reaches), r (the
    #    level's radius), hemi, px, pz (the pole on the map), src}
    cps = []
    try:
        objs = bf2.objectManager.getObjectsOfType(CP_TYPE)
    except:
        objs = []
    for cp in objs:
        try:
            p = cp.getPosition()
            cps.append((cp, (float(p[0]), float(p[1]), float(p[2]))))
        except:
            pass
    if not cps:
        return None
    lay = FLAGS.get(mp, {})
    best = None
    for key in lay.keys():
        L = lay[key]
        ok = 0
        for cp, p in cps:
            if near_entry(L, p[0], p[2]) is not None:
                ok = ok + 1
        sc = ok * 10 - (len(cps) - ok) * 20 - abs(len(L) - len(cps))
        if key[:6] == 'gpm_cq':
            sc = sc + 0.5
        if best is None or sc > best[0]:
            best = (sc, key, L, ok)
    L = []
    S['layout'] = None
    if best is not None and best[3] > 0:
        L = best[2]
        S['layout'] = best[1]
    zones = []
    left = []
    for cp, p in cps:
        e = near_entry(L, p[0], p[2])
        if e is not None:
            name, r, main, ox, oy, oz, hemi, src = e[0], e[3], e[4], e[5], e[6], e[7], e[8], 'data'
        else:
            name = 'at %.0f %.0f' % (p[0], p[2])
            ox, oy, oz = 0.0, 0.0, 0.0
            r, src = cp_radius(cp), 'game'
            if r is None:
                r, src = UNKNOWN_RADIUS, 'default'
            hemi = cp_param(cp, 'isHemisphere') == 1
            main = cp_param(cp, 'unableToChangeTeam') == 1
            if r <= 0:
                left.append(name + ' (no radius)')
                continue
        if main and not MAIN_BASES:
            left.append(name + ' (main base)')
            continue
        zones.append({'name': name, 'x': p[0] + ox, 'h': p[1] + oy, 'z': p[2] + oz, 'R': r + ZONE_FOOT + ZONE_EXTRA,
                      'r': r, 'hemi': hemi, 'px': p[0], 'pz': p[2], 'src': src})
    S['left'] = left
    return zones

def zone_at(pos):
    # (zone, m from the pole on the map) of the flag zone a claymore at pos (x, height, z) lies in, or None
    best = None
    for z in S['zones'] or []:
        dx, dz, dy = pos[0] - z['x'], pos[2] - z['z'], pos[1] + SOLDIER_UP - z['h']
        if z['hemi'] and dy < 0:
            continue
        if dx * dx + dy * dy + dz * dz > z['R'] * z['R']:
            continue
        d = ((pos[0] - z['px']) ** 2 + (pos[2] - z['pz']) ** 2) ** 0.5
        if best is None or d < best[1]:
            best = (z, d)
    return best

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

def fan_hit(pos, face):
    # (zone, m from the pole on the map, m the fan reaches into the zone) of the zone the claymore's trigger fan reaches
    # into the most, or None (a soldier standing in the fan is on the claymore's level: his position 1 m over it)
    best = None
    for z in S['zones'] or []:
        dy = pos[1] + SOLDIER_UP - z['h']
        if z['hemi'] and dy < 0:
            continue
        if dy * dy >= z['R'] * z['R']:
            continue
        r = (z['R'] * z['R'] - dy * dy) ** 0.5     # (the zone's circle on that level)
        into = r - fan_gap(z['x'], z['z'], pos[0], pos[2], face)
        if into < 0:
            continue
        d = ((pos[0] - z['px']) ** 2 + (pos[2] - z['pz']) ** 2) ** 0.5
        if best is None or into > best[2]:
            best = (z, d, into)
    return best

def nearest_flag(pos):
    best = None
    for z in S['zones'] or []:
        d = ((pos[0] - z['px']) ** 2 + (pos[2] - z['pz']) ** 2) ** 0.5
        if best is None or d < best[1]:
            best = (z, d)
    return best


def fan_hits(pos, face):
    # [(zone, m from the pole on the map, m the fan reaches into the zone)] of every zone the claymore's trigger fan
    # reaches into, deepest first
    out = []
    for z in S['zones'] or []:
        dy = pos[1] + SOLDIER_UP - z['h']
        if z['hemi'] and dy < 0:
            continue
        if dy * dy >= z['R'] * z['R']:
            continue
        r = (z['R'] * z['R'] - dy * dy) ** 0.5
        into = r - fan_gap(z['x'], z['z'], pos[0], pos[2], face)
        if into < 0:
            continue
        d = ((pos[0] - z['px']) ** 2 + (pos[2] - z['pz']) ** 2) ** 0.5
        out.append((-into, d, z['name'], z))
    out.sort()
    L = []
    for n, d, nm, z in out:
        L.append((z, d, -n))
    return L

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

def zone_lines(pos, face, fans):
    # the lines to try for a claymore at pos facing face whose fan reaches the zones fans
    ups = numbers(CHARGE_UP, [0.15, 0.4])
    bodies = numbers(BODY_UP, [0.3, 0.9, 1.5])
    lows = low_pairs()
    step_a = SAMPLE_ANGLE
    if step_a <= 0:
        step_a = 15.0
    step_d = SAMPLE_STEP
    if step_d <= 0:
        step_d = 1.5
    dirs = []
    if face is None:
        k = 0
        while k * step_a < 360.0 - 0.001:
            dirs.append(k * step_a)
            k = k + 1
    else:
        n = int(BLAST_ANGLE / step_a + 0.001)
        for k in range(-n, n + 1):
            dirs.append(face + k * step_a)
        if n * step_a < BLAST_ANGLE - 0.001:
            dirs.append(face - BLAST_ANGLE)
            dirs.append(face + BLAST_ANGLE)
    dists = []
    d = step_d / 2.0
    while d <= BLAST_REACH + 0.001:
        dists.append(d)
        d = d + step_d
    lines = []
    for z, dz_, into in fans:
        dy = pos[1] + SOLDIER_UP - z['h']
        r2 = z['R'] * z['R'] - dy * dy        # (the zone's circle on the claymore's level)
        T = []
        for a in dirs:
            s, c = sin_cos(a)
            for d in dists:
                sx, sz = pos[0] + d * s, pos[2] + d * c
                if (sx - z['x']) ** 2 + (sz - z['z']) ** 2 <= r2:
                    T.append((d, sx, sz))
        if not T and r2 > 0:
            # the zone's point nearest to the claymore
            vx, vz = z['x'] - pos[0], z['z'] - pos[2]
            L0 = (vx * vx + vz * vz) ** 0.5
            rr = r2 ** 0.5
            if L0 > rr and L0 > 1e-6:
                k = (L0 - rr) / L0
                T.append((L0 - rr, pos[0] + vx * k, pos[2] + vz * k))
            else:
                T.append((0.0, pos[0], pos[2]))
        T.sort()             # (the nearest first)
        for d, sx, sz in T:
            for b in (bodies[len(bodies) // 2:] + bodies[:len(bodies) // 2]):
                for u in ups:
                    lines.append((pos[0], pos[1] + u, pos[2], sx, pos[1] + b, sz, (z['name'], d, u, b)))
            for u, b in lows:
                lines.append((pos[0], pos[1] + u, pos[2], sx, pos[1] + b, sz, (z['name'], d, u, b)))
    return lines

def line_text(L):
    nm, d, u, b = L[6]
    return 'from %.2f m over it to %.2f m over the ground %.1f m out, in the zone of %s' % (u, b, d, nm)

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
            x['verdict'] = None
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
            x['verdict'] = 'remove'
            found(r, x, r['pos'], None, t, x['face'], x['fans'][0], why)
    S['jobs'] = keep

def left_by_walls(r, x, res, ms, n):
    pos = r['pos']
    z, d, into = x['fans'][0]
    x['verdict'] = 'left'
    tl = tally_of(z['name'])
    tl[4] = tl[4] + 1
    S['left_n'] = S['left_n'] + 1
    names = []
    for q, dd, ii in x['fans']:
        names.append(q['name'])
    what = 'its trigger fan (%.0f m, %.0f deg each side, %s)' % (TRIGGER_RADIUS, TRIGGER_ANGLE, face_text(x['face']))
    if x['face'] is None:
        what = 'its trigger (%s: a %.0f m circle)' % (face_text(x['face']), TRIGGER_RADIUS)
    log('%s: claymore %s by the flag %s, %.1f m from the pole, outside the zone (%.1f m round it), but %s reaches %.1f m '
        'into it, at (%.2f, %.2f, %.2f) [%.2f s after it appeared] - LEFT: walled off from the zone%s inside its blast '
        'cone (%.0f deg each side, %.1f m): all %d lines blocked (%s) [%.1f ms]' % (S['map'], r['id'], ', '.join(names),
        d, z['R'], what, into, pos[0], pos[1], pos[2], x['t_judged'] - r['t0'], (len(names) > 1 and 's') or '',
        BLAST_ANGLE, BLAST_REACH, n, WALLS_MOD.walls_text(res[1]), ms))
    test_say('claymore %s by the flag %s: its trigger reaches %.1f m into the zone - LEFT: behind %s (%d lines)' % (
        r['id'], ', '.join(names), into, WALLS_MOD.walls_text(res[1], 2), n))

# ------------------------------------------------------------------ what was found
def tally_of(flag):
    tl = S['tally'].get(flag)
    if tl is None:
        tl = [0, 0, 0, 0, 0]     # found, removed, only sent to the sky, by the fan, left by the walls
        S['tally'][flag] = tl
    return tl

def face_text(face):
    if face is None:
        return 'facing unknown'
    return 'facing %.0f deg (%s)' % (face, compass(face))

def found(r, x, pos, hit, t, face, fan=None, why=''):
    if fan is not None:
        z, d, into = fan
    else:
        z, d = hit
    x['flag'] = z['name']
    tl = tally_of(z['name'])
    tl[0] = tl[0] + 1
    if why:
        why = '; ' + why
    if fan is None:
        log('%s: claymore %s at the flag %s, %.1f m from the pole (zone %.1f m round it, in 3D) at (%.2f, %.2f, %.2f), '
            '%s [%.2f s after it appeared] - removing' % (S['map'], r['id'], z['name'], d, z['R'], pos[0], pos[1],
            pos[2], face_text(face), t - r['t0']))
        test_say('claymore %s at %.1f %.1f %.1f: IN the zone of %s (%.1f m from the pole) - removing' % (
            r['id'], pos[0], pos[2], pos[1], z['name'], d))
    else:
        tl[3] = tl[3] + 1
        what = 'its trigger fan (%.0f m, %.0f deg each side, %s)' % (TRIGGER_RADIUS, TRIGGER_ANGLE, face_text(face))
        if face is None:
            what = 'its trigger (%s: a %.0f m circle)' % (face_text(face), TRIGGER_RADIUS)
        log('%s: claymore %s by the flag %s, %.1f m from the pole, outside the zone (%.1f m round it), but %s reaches '
            '%.1f m into it, at (%.2f, %.2f, %.2f) [%.2f s after it appeared]%s - removing' % (S['map'], r['id'],
            z['name'], d, z['R'], what, into, pos[0], pos[1], pos[2], t - r['t0'], why))
        test_say('claymore %s at %.1f %.1f %.1f, %s: its trigger reaches %.1f m into the zone of %s - removing' % (
            r['id'], pos[0], pos[2], pos[1], face_text(face), into, z['name']))
    BUS.remove(F, r, t, 'at the flag %s' % z['name'])

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
def zones_ready(t):
    if S['zones'] is not None:
        return 1
    if t - S['zone_try'] < 2.0:
        return 0
    S['zone_try'] = t
    z = load_zones(S['map'])
    if z is None:
        if t - S['round_t'] > 60 and not S['warned'].get('noflags'):
            S['warned']['noflags'] = 1
            log('round on %s: the game shows no flags - nothing to watch' % S['map'])
        return 0
    S['zones'] = z
    names = []
    for q in z:
        names.append('%s %.0f+%.1f m%s' % (q['name'], q['r'], q['R'] - q['r'], (q['src'] != 'data' and ' (radius: %s)' %
            q['src']) or ''))
    lay = S['layout'] or 'no data for this map'
    log('round on %s (layout %s): %d flag%s watched: %s%s' % (S['map'], lay, len(z), (len(z) != 1 and 's') or '',
        ', '.join(names), (S['left'] and '; left out: ' + ', '.join(S['left'])) or ''))
    return 1

def new_x():
    # verdict (read by mm_spawnclay_walls): None - not judged; 'pending' - its walls check goes on; 'remove'; 'left' (the
    # walls); 'none' - not claycap's (not in a zone, its fan reaches none); v_still - the rest it was judged at
    return {'judged': None, 'flag': None, 'told': 0, 'job': None, 'job_t': 0.0, 'fans': None, 'face': None,
            't_judged': 0.0, 'verdict': None, 'v_still': None}

def look(t):
    if S['idle']:
        return
    ready = zones_ready(t)
    for r in BUS.track('claymore', t):
        if not r['upd']:
            continue
        x = r['x'].get(NAME)
        if x is None:
            x = new_x()
            r['x'][NAME] = x
        if r['rm'] is not None:
            continue                      # (being removed - by claycap_walls or by spawnclay: the bus follows it)
        pos = r['pos']
        if pos[1] < BUS.BELOW_MAP:
            continue
        if x['job'] is not None:
            continue                      # (its walls check goes on in run_walls)
        # judged once it has lain still REST_TIME (again if it moves and comes to rest again)
        if not ready or x['judged'] == r['still'] or t - r['still'] < REST_TIME:
            continue
        x['judged'] = r['still']
        x['v_still'] = r['still']
        x['t_judged'] = t
        face = face_of(r['o'])
        hit = zone_at(pos)
        fans = []
        if hit is None and FAN_RULE and (face is not None or UNKNOWN_FACE):
            fans = fan_hits(pos, face)
        if hit is not None:
            x['verdict'] = 'remove'
            found(r, x, pos, hit, t, face)
        elif fans:
            x['fans'], x['face'] = fans, face
            if walls_on():
                x['verdict'] = 'pending'
                x['job'] = walls_job(zone_lines(pos, face, fans))
                x['job_t'] = t
                S['jobs'].append(r)
            else:
                x['verdict'] = 'remove'
                found(r, x, pos, None, t, face, fans[0])
        else:
            x['verdict'] = 'none'
            if TEST_CHAT:
                nf = nearest_flag(pos)
                where = 'no flag watched'
                if nf is not None:
                    z = nf[0]
                    where = 'nearest flag %s %.1f m from its pole, zone %.1f m' % (z['name'], nf[1], z['R'])
                    if FAN_RULE:
                        gap = fan_gap(z['x'], z['z'], pos[0], pos[2], face)
                        where = where + '; its trigger stays %.1f m short of the pole' % gap
                test_say('claymore %s at %.1f %.1f %.1f, %s: not in a flag zone (%s)' % (r['id'], pos[0], pos[2],
                    pos[1], face_text(face), where))
    run_walls(t)

# ------------------------------------------------------------------ rounds
def find_mod(name):
    m = sys.modules.get(name)
    if m is not None:
        return m
    for k in sys.modules.keys():
        if k[-(len(name) + 1):] == '.' + name and sys.modules[k] is not None:
            return sys.modules[k]
    return None

def round_start(t):
    S['map'] = BUS.S['map']
    S['zones'] = None
    S['layout'] = None
    S['left'] = []
    S['round_t'] = t
    S['zone_try'] = -99.0
    S['tally'] = {}
    S['ways'] = {}
    S['jobs'] = []
    S['left_n'] = 0
    S['idle'] = 0
    S['walls0'] = (WALLS_MOD.STATS['lines'], WALLS_MOD.STATS['faces'])
    if 'noflags' in S['warned']:
        del S['warned']['noflags']
    if find_mod('mm_claycap') is not None:
        S['idle'] = 1
        log('round on %s: mm_claycap is loaded as well - claycap_walls stays idle (load only one of the two)' % S['map'])
        return
    if WALLS and not WALLS_MOD.has_map(S['map']):
        log('round on %s: mm_flwalls has no walls for this map - every claymore whose fan reaches a zone is removed, as '
            'without walls' % S['map'])
    not_walls()              # (made now, not in the first check)
    zones_ready(t)

def round_end(t):
    if S['idle']:
        log('round summary on %s: idle' % S['map'])
        S['tally'] = {}
        S['ways'] = {}
        return
    L = []
    n = r = k = w = 0
    for name in S['tally'].keys():
        tl = S['tally'][name]
        n, r, k, w = n + tl[0], r + tl[1], k + tl[2], w + tl[4]
        L.append((-(tl[0] + tl[4]), name, tl))
    L.sort()
    parts = []
    lefts = []
    for z, name, tl in L:
        if tl[0]:
            extra = ''
            if tl[3]:
                extra = '; %d of them by the trigger fan' % tl[3]
            parts.append('%s %d (removed %d%s)' % (name, tl[0], tl[1], extra))
        if tl[4]:
            lefts.append('%s %d' % (name, tl[4]))
    ways = []
    for wy in S['ways'].keys():
        ways.append('%s %d' % (wy, S['ways'][wy]))
    ways.sort()
    lw = ''
    if w:
        lw = '; left by the walls (the fan reaches a zone, but walled off from it): %d - %s' % (w, ', '.join(lefts))
    seen = BUS.seen_n('claymore')
    if n:
        log('round summary on %s: %d claymores seen, %d in or into flag zones - %s; removed %d (%s), only sent to the '
            'sky %d, not removed %d%s' % (S['map'], seen, n, '; '.join(parts), r, ', '.join(ways) or '-', k, n - r - k,
            lw))
    else:
        log('round summary on %s: %d claymores seen, none in flag zones%s' % (S['map'], seen, lw))
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
def claycap_init():
    global F
    F = BUS.feature(NAME, 'Claymore', LOG_FILE, 'ClayCap')
    F.log_file = LOG_FILE
    F.maps = MAPS
    F.every = CHECK_EVERY
    F.look = look
    F.round_start = round_start
    F.round_end = round_end
    F.on_removed = on_removed
    F.on_sky = on_sky
    F.ghost_check = 0            # (a claymore sent under the map is removed: the 07.11 test)
    F.test_chat = TEST_CHAT
    extra = ''
    if MAIN_BASES:
        extra = '; main bases too'
    if not SAY:
        extra = extra + '; nothing said in the chat'
    if TEST_CHAT:
        extra = extra + '; TEST_CHAT is on'
    if FAN_RULE:
        extra = '; also a claymore whose trigger fan (%.0f m, %.0f deg each side) reaches into a zone%s' % (
            TRIGGER_RADIUS, TRIGGER_ANGLE, (UNKNOWN_FACE and ' - a %.0f m circle if its face is unknown' % TRIGGER_RADIUS)
            or '') + extra
        if FACE_OFFSET or FACE_MIRROR:
            extra = extra + '; face: yaw%s + %.0f deg' % ((FACE_MIRROR and ' mirrored') or '', FACE_OFFSET)
        if WALLS:
            extra = extra + ('; such a one LEFT if walled off from the zone inside its blast cone (%.0f deg each side, '
                '%.1f m; points every %.0f deg and %.1f m): %s; %.0f ms a look; walls: mm_flwalls %s, %s' % (
                BLAST_ANGLE, BLAST_REACH, SAMPLE_ANGLE, SAMPLE_STEP, walls_setup_text(), WALL_MS, WALLS_MOD.VERSION,
                WALLS_MOD.map_text('strike_at_karkand')))
        else:
            extra = extra + '; WALLS 0: walls not taken into account'
    log('claycap_walls %s loaded, on mm_flbus %s (maps: %s; zones: the flag\'s radius + %.1f m - one lying in a zone is '
        'removed, walls or not; removed by the bus: down, lift + down, cut, sky - see flbus.log; nobody punished%s)' % (
        VERSION, BUS.VERSION, MAPS, ZONE_FOOT + ZONE_EXTRA, extra))
    BUS.add(F)

# ------------------------------------------------------------------ data
# each map's flags per layout (game mode : size), from the level files (BF2 Round Replay v271):
# (name, x, z (north), the level's radius m, main base 1, radiusOffset x, up, north, isHemisphere 1)
# Only the maps in MAPS are watched; the others are here for later.
FLAGS = {
    'dalian_plant': {
        'gpm_coop:16': [
            ('Reactors', 88.0, -40.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -151.8, -58.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Main Entrance', -254.0, -210.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power plant', -92.3, -260.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('Reactor Towers', 88.0, -40.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -151.8, -58.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Main Entrance', -254.0, -210.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power Plant', -92.3, -260.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('US Carrier', 786.0, 49.7, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Reactor Towers', 88.0, -40.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Main Entrance', -254.0, -210.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('South Docks', 246.8, -242.4, 24.0, 0, 0.0, 0.0, 0.0, 0),
            ('Airfield', -707.0, -367.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Maintenance Buildings', -32.5, -391.2, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('North Docks', 52.0, 184.0, 22.0, 0, 0.0, 0.0, 0.0, 0),
            ('Warehouse', -190.3, 54.7, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('US Carrier', 786.0, 49.7, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Reactor Towers', 88.0, -40.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Main Entrance', -254.0, -210.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('South Docks', 246.8, -242.4, 24.0, 0, 0.0, 0.0, 0.0, 0),
            ('Airfield', -706.0, -367.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Maintenance Buildings', -32.6, -391.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Reactors', 88.0, -40.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -151.8, -58.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Main Entrance', -254.0, -210.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power plant', -92.3, -260.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'daqing_oilfields': {
        'gpm_coop:16': [
            ('Old city', 129.0, 255.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Oil cisterns', 67.8, -43.9, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', -53.5, -243.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('Old City', 129.0, 255.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Oil Cisterns', 67.8, -43.9, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', -53.5, -243.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Chinese Base', -245.7, 380.4, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Old City', 129.0, 255.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power Station', -212.0, 21.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Oil Cisterns', 67.8, -43.9, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Gas Station', 319.0, -103.0, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', -53.5, -243.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('US Town', 346.0, -578.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Chinese Base', -245.7, 380.4, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Old City', 129.0, 255.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('East Oilfield', 486.0, 175.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power Station', -212.0, 21.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Oil Cisterns', 67.8, -43.9, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Gas Station', 319.0, -103.0, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('West Oilfield', -363.7, -115.2, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', -53.5, -243.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('US Town', 346.0, -578.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Old city', 129.0, 255.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Oil cisterns', 67.8, -43.9, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', -53.5, -243.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'dragon_valley': {
        'gpm_coop:16': [
            ('Wood Yard', -298.4, -192.3, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hill Village', -50.5, -227.4, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power station', -211.4, -430.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', 122.6, -562.2, 9.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('Wood Yard', -298.4, -192.3, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hill Village', -50.5, -227.4, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power station', -211.4, -430.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', 122.6, -562.2, 9.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Market Place', 116.1, 314.2, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Island Farmhouse', -78.0, 100.0, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Wood Yard', -298.4, -192.3, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hill Village', -50.5, -227.3, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power station', -211.4, -430.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', 122.5, -562.1, 9.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Docks', -225.1, 875.9, 9.0, 0, 0.0, 0.0, 0.0, 0),
            ('US Carrier', 382.6, 822.5, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Vista Point', 74.9, 588.7, 7.0, 0, 0.0, 0.0, 0.0, 0),
            ('River Village', -224.0, 479.0, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Temple', -83.1, 410.2, 9.0, 0, 0.0, 0.0, 0.0, 0),
            ('Market Place', 116.1, 314.2, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Island Farmhouse', -78.0, 100.0, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Wood Yard', -298.4, -192.4, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hill Village', -50.5, -227.4, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power station', -211.3, -430.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', 122.4, -562.2, 9.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Wood Yard', -298.4, -192.3, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hill Village', -50.5, -227.4, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power station', -211.4, -430.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', 122.6, -562.2, 9.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'fushe_pass': {
        'gpm_coop:16': [
            ('East Mine Entrance', 139.2, 128.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('West Mine Entrance', -150.3, -24.4, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Island', 94.4, -37.0, 5.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('East Mine Entrance', 139.2, 128.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('West Mine Entrance', -150.3, -24.4, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Island', 94.4, -37.0, 5.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Bridge Camp', -248.9, 287.5, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Upper Camp', -531.5, 231.7, 8.0, 1, 0.0, 0.0, 0.0, 0),
            ('East Mine Entrance', 139.2, 128.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('West Mine Entrance', -150.3, -24.4, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Security Headquarters', 83.0, -199.1, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power Plant', 302.0, -203.0, 9.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('US Airfield', 608.6, 576.8, 5.0, 1, 0.0, 0.0, 0.0, 0),
            ('Bridge Camp', -248.9, 287.5, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Upper Camp', -531.5, 231.7, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('East Mine Entrance', 139.2, 128.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Mountain Lookout', 276.8, 125.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('West Mine Entrance', -150.3, -24.4, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Canyon Guard Post', -273.9, -130.7, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Security Headquarters', 83.0, -199.0, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power Plant', 302.0, -203.0, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Chinese Airfield', -668.1, -493.8, 6.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('East Mine Entrance', 139.2, 128.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('West Mine Entrance', -150.3, -24.4, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Island', 94.4, -37.0, 5.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'greatwall': {
        'gpm_coop:16': [
            ('Quan Compound', 16.4, 55.1, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Fortress Village', -203.0, -4.0, 12.0, 0, 3.0, 0.0, 0.0, 0),
            ('Central Wall', -56.5, -24.9, 10.0, 0, 0.0, 0.0, 0.0, 1),
            ('Compound Wall', 68.9, -34.3, 10.0, 1, 0.0, 0.0, 0.0, 1),
            ('Quan Temple', -157.9, -62.6, 10.0, 0, 0.0, 0.0, 0.0, 1),
            ('Compound Gate Village', -18.0, -64.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('EU Strike Point', -250.0, 94.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Compound Main Village', 15.0, 37.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Quan Tower', -58.5, 13.7, 9.5, 0, 0.0, -10.0, 0.0, 0),
            ('Fortress Village', -203.0, -4.0, 12.0, 0, 3.0, 0.0, 0.0, 0),
            ('Quan Temple', -113.0, -41.0, 17.0, 0, 0.0, 0.0, -8.0, 1),
            ('Compound Gate Village', -18.0, -64.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Huang Village', 128.0, 255.8, 18.0, 1, -5.0, 0.0, 0.0, 0),
            ('Lao Tian Ye Road', -306.0, 100.0, 18.0, 0, 0.0, 0.0, 0.0, 0),
            ('Quan Compound', 9.0, 36.0, 14.0, 0, 2.0, 0.0, 0.0, 0),
            ('Lao Seng Hill', 204.0, -56.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('Quan Fortress', -158.0, -70.0, 20.0, 0, 0.0, -7.5, 7.5, 0),
            ('Cam Yin', -233.0, -264.0, 18.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Quan Compound', 16.4, 55.1, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Fortress Village', -203.0, -4.0, 12.0, 0, 3.0, 0.0, 0.0, 0),
            ('Central Wall', -56.5, -24.9, 10.0, 0, 0.0, 0.0, 0.0, 1),
            ('Compound Wall', 68.9, -34.3, 10.0, 1, 0.0, 0.0, 0.0, 1),
            ('Quan Temple', -157.9, -62.6, 10.0, 0, 0.0, 0.0, 0.0, 1),
            ('Compound Gate Village', -18.0, -64.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:32': [
            ('32_China_CP_Liu_Shu_CHun_VIllage', -50.0, 506.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('32_China_CP_Huang_VIllage', 128.0, 255.8, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_China_CP_Lao_Tian_Ye_Road', -278.0, 90.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_None_CP_Quan_Compound', 18.0, 34.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_None_CP_Quan_Fortress', -119.4, -39.6, 15.0, 0, 0.0, -5.0, 0.0, 0),
            ('32_EU_CP_Lao_Seng_Hill', 204.0, -56.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_EU_CP_Cam_Yin', -233.0, -264.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_EU_CP_Wei_Tian_Village', -84.0, -512.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:64': [
            ('32_China_CP_Liu_Shu_CHun_VIllage', -50.0, 506.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('32_China_CP_Huang_VIllage', 128.0, 255.8, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_China_CP_Lao_Tian_Ye_Road', -278.0, 90.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_None_CP_Quan_Compound', 18.0, 34.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_None_CP_Quan_Fortress', -119.4, -39.6, 15.0, 0, 0.0, -5.0, 0.0, 0),
            ('32_EU_CP_Lao_Seng_Hill', 204.0, -56.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_EU_CP_Cam_Yin', -233.0, -264.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_EU_CP_Wei_Tian_Village', -84.0, -512.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
    },
    'gulf_of_oman': {
        'gpm_coop:16': [
            ('Construction Site', 49.4, 33.5, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('City', 124.8, -46.1, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Village', 10.2, -136.4, 6.5, 0, 0.0, 0.0, 0.0, 0),
            ('Beach', 34.0, -296.2, 6.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('Construction Site', 49.4, 33.5, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('City', 124.8, -46.1, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Village', 10.3, -136.4, 6.5, 0, 0.0, 0.0, 0.0, 0),
            ('Beachhead', 34.0, -296.2, 6.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Airfield Base', 282.0, 215.6, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Construction Site', 49.4, 33.5, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('River Fortification', -331.5, 28.2, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hotel', 281.8, -94.7, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Olive Hill Fortification', -208.4, -141.2, 7.0, 0, 0.0, 0.0, 0.0, 0),
            ('Rock Fortification', -65.2, -202.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('US Carrier', -664.6, -553.5, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Airfield Base', 282.0, 215.6, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Village', -133.0, 176.2, 4.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', 49.4, 33.5, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('River Fortification', -331.5, 28.2, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hotel', 281.8, -94.7, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Olive Hill Fortification', -208.4, -141.1, 7.0, 0, 0.0, 0.0, 0.0, 0),
            ('Rock Fortification', -65.2, -202.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Village Fortification', 118.0, -253.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('US Carrier', -664.6, -553.5, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Construction Site', 49.4, 33.5, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('City', 124.8, -46.1, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Village', 10.2, -136.4, 6.5, 0, 0.0, 0.0, 0.0, 0),
            ('Beach', 34.0, -296.2, 6.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'highway_tampa': {
        'gpm_cq:16': [
            ('Refinery', 106.0, -334.0, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Sharhr Urmia', 608.0, -526.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Village of Kuhlaz', 176.8, -614.2, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Checkpoint South', -284.6, -781.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Airfield', -493.0, 636.5, 15.0, 1, 0.0, 0.0, 0.0, 0),
            ('Village of Buhifum', -290.7, -21.1, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', 106.0, -334.0, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Gas Station', -231.7, -503.5, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Sharhr Urmia', 608.0, -526.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Village of Kuhlaz', 176.8, -614.2, 13.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Airfield', -493.0, 636.5, 15.0, 1, 0.0, 0.0, 0.0, 0),
            ('Village of Buhifum', -290.7, -21.1, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refinery', 105.9, -333.9, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Checkpoint West', -729.0, -497.0, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Gas Station', -231.7, -503.5, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Sharhr Urmia', 608.0, -526.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Village of Kuhlaz', 176.9, -614.3, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Checkpoint South', -284.6, -781.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'kubra_dam': {
        'gpm_cq:16': [
            ('Power Station', -495.0, -105.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Lower Dam', -401.6, -223.4, 17.0, 0, 0.0, 0.0, 0.0, 0),
            ('Upper Dam', -426.8, -244.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -205.5, -274.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Abandoned Huts', 162.0, 184.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Material Station', -354.0, 156.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Bridge Base', -72.8, 105.1, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refueling Station', -260.0, -14.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power Station', -495.0, -105.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Lower Dam', -401.6, -223.4, 17.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -205.5, -274.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Intake', -388.9, -520.2, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Supervisor Base', -220.0, 294.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Abandoned Huts', 162.0, 184.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Material Station', -354.0, 156.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Bridge Base', -72.8, 105.1, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refueling Station', -260.0, -14.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power Station', -495.0, -105.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Lower Dam', -401.6, -223.4, 17.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -205.5, -274.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Intake', -388.9, -520.2, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'mashtuur_city': {
        'gpm_cq:16': [
            ('Hotel', -261.9, -21.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('North Bridge', -173.0, -89.0, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Road Construction', -241.2, -161.4, 4.0, 0, 0.0, 0.0, 0.0, 0),
            ('South Block', -151.8, -222.3, 7.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Hotel', -262.0, -21.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hill', -7.5, -82.2, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Mosque', -159.0, -118.3, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power Plant', -368.6, -212.4, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Backyard', -112.0, -222.3, 7.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('North Gas Station', -404.0, 188.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hotel', -262.0, -21.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hill', -7.5, -82.2, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Mosque', -159.0, -118.3, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Power Plant', -368.6, -212.4, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Backyard', -112.0, -222.3, 7.0, 0, 0.0, 0.0, 0.0, 0),
            ('South Gas Station', 103.9, -322.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'midnight_sun': {
        'gpm_coop:16': [
            ('Construction Office', -193.1, -56.7, 17.0, 0, 0.0, 0.0, 0.0, 0),
            ('Church', -385.1, -97.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Village', -488.0, -143.5, 10.0, 0, 0.0, 0.0, 2.0, 0),
            ('Gas Station', -199.5, -193.1, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('Construction Office', -188.7, -56.7, 17.0, 0, -4.0, 0.0, 0.0, 0),
            ('Church', -385.1, -97.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Village', -488.0, -143.5, 10.0, 0, 0.0, 0.0, 2.0, 0),
            ('Gas Station', -199.5, -193.1, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Salmon Pass', 550.6, 5.3, 20.0, 1, 0.0, 0.0, 0.0, 0),
            ('Construction Office', -179.9, -56.8, 17.0, 0, 0.0, 0.0, 0.0, 0),
            ('Pumping Station', 248.4, -136.6, 20.0, 0, 0.0, -17.5, 0.0, 0),
            ('Valdez', -488.0, -143.5, 10.0, 0, 0.0, 0.0, 2.0, 0),
            ('Pipeline Valve', 13.6, -272.8, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('River Airbase', -618.0, -305.2, 20.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Salmon Pass', 550.6, 5.3, 20.0, 1, 0.0, 0.0, 0.0, 0),
            ('Radio Tower', 47.0, -20.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Office', -179.9, -56.8, 17.0, 0, 0.0, 0.0, 0.0, 0),
            ('Pumping Station', 248.4, -136.6, 20.0, 0, 0.0, -17.5, 0.0, 0),
            ('Valdez', -488.0, -143.5, 10.0, 0, 0.0, 0.0, 2.0, 0),
            ('Pipeline Valve', 13.6, -272.8, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('River Airbase', -618.0, -305.2, 20.0, 1, 0.0, 0.0, 0.0, 0),
            ('Oil Port', -252.9, -373.4, 20.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Construction Office', -193.1, -56.7, 17.0, 0, 0.0, 0.0, 0.0, 0),
            ('Church', -385.1, -97.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Village', -488.0, -143.5, 10.0, 0, 0.0, 0.0, 2.0, 0),
            ('Gas Station', -199.5, -193.1, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'operation_blue_pearl': {
        'gpm_cq:16': [
            ('Construction Site', -304.1, -66.0, 14.0, 0, 0.0, 0.0, 0.0, 0),
            ('Old Square', -103.3, -74.1, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Yard', -252.0, -162.8, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Market', -75.2, -196.9, 14.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Construction Site', -304.0, -66.0, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Old Square', -103.1, -74.0, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Temple', 19.8, -94.1, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('Industrial Harbor', 260.2, -109.2, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Fish Market', -184.0, -128.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Yard', -251.9, -164.0, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Market', -75.2, -196.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Harbor Office', -296.5, 84.0, 4.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -304.0, -65.9, 13.0, 0, 0.0, 0.0, 0.0, 0),
            ('Old Square', -103.3, -74.1, 12.0, 0, 0.0, 0.0, 0.0, 0),
            ('Temple', 19.8, -94.0, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('Industrial Harbor', 260.2, -109.2, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Fish Market', -184.0, -128.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Yard', -251.9, -164.0, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Market', -75.1, -197.2, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'operation_clean_sweep': {
        'gpm_coop:16': [
            ('Airfield', -552.0, 544.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Control Center', -538.0, -36.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refueling Station', -308.1, -422.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Small Airstrip', -42.0, -424.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('Airfield', -552.0, 544.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Control Center', -538.0, -36.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refueling Station', -308.1, -422.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Small Airstrip', -42.0, -424.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Airfield', -552.0, 544.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Control Center', -538.0, -36.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Communication Central', 229.9, -364.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refueling Station', -308.1, -422.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Small Airstrip', -42.0, -424.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Abandoned Village', 142.0, -598.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Airfield', -552.0, 544.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Control Center', -538.0, -36.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('MEC Airfield', 644.0, -96.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Harbor', 614.0, -281.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Communication Central', 229.9, -364.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refueling Station', -308.1, -422.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Small Airstrip', -42.0, -424.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Abandoned Village', 142.0, -598.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Airfield', -552.0, 544.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Control Center', -538.0, -36.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Refueling Station', -308.1, -422.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Small Airstrip', -42.0, -424.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'operationharvest': {
        'gpm_coop:16': [
            ('MEC Field Base', 472.1, 435.7, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Dairy Farm', 183.8, 310.6, 20.0, 0, 2.0, -5.0, -8.0, 0),
            ('Grain Elevator', 386.9, 197.4, 17.0, 0, -11.0, 0.0, 4.0, 0),
            ('US Forward Post', 180.1, 79.9, 15.0, 0, 0.0, 0.0, 0.0, 1),
        ],
        'gpm_cq:16': [
            ('MEC Field Base', 472.1, 435.7, 15.0, 1, 0.0, 0.0, 0.0, 0),
            ('Dairy Farm', 184.0, 310.7, 19.0, 0, 2.0, -5.0, -8.0, 0),
            ('Grain Elevator', 386.9, 197.4, 17.0, 0, -11.0, 0.0, 4.0, 0),
            ('US Forward Post', 180.1, 79.9, 15.0, 0, 0.0, 0.0, 0.0, 1),
            ('Checkpoint Barndoor', -136.5, -68.2, 15.0, 0, 0.0, 0.0, 5.0, 0),
        ],
        'gpm_cq:32': [
            ('MEC Field Camp', 199.3, 568.6, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Dairy Farm', 183.8, 310.6, 19.0, 0, 2.0, -5.0, -8.0, 0),
            ('Grain Elevator', 386.3, 196.8, 17.0, 0, -10.0, 0.0, 4.0, 0),
            ('MEC Scout Post', 180.3, 80.5, 15.0, 0, 0.0, 0.0, 0.0, 1),
            ('Checkpoint Barndoor', -137.6, -68.4, 15.0, 0, 0.0, 0.0, 6.0, 0),
            ('Field Equipment Barn', -383.0, -74.3, 20.0, 0, -8.0, -5.0, -6.0, 0),
            ('Large Produce Farm', -253.4, -296.8, 23.0, 0, 0.0, 0.0, 0.0, 0),
            ('Apple Cider Farm', -438.6, -487.3, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('MEC Field Base', 199.3, 568.4, 20.0, 0, 0.0, 0.0, 0.0, 0),
            ('Dairy Farm', 184.0, 310.6, 19.0, 0, 3.0, -5.0, -8.0, 0),
            ('Grain Elevator', 386.6, 197.4, 17.0, 0, -9.0, 0.0, 5.0, 0),
            ('MEC Scout Post', 180.2, 80.5, 15.0, 0, 0.0, 0.0, 0.0, 1),
            ('Checkpoint Barndoor', -137.3, -68.3, 15.0, 0, 0.0, 0.0, 6.0, 0),
            ('Hilltop Overlook', 135.3, -260.2, 20.0, 0, -8.0, 0.0, -10.0, 0),
            ('Large Produce Farm', -253.6, -296.9, 23.0, 0, 0.0, 0.0, 0.0, 0),
            ('Armored Convoy', 350.7, -482.9, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('US Strike Operations Base', -438.5, -487.3, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('MEC Field Base', 472.1, 435.7, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Dairy Farm', 183.8, 310.6, 20.0, 0, 2.0, -5.0, -8.0, 0),
            ('Grain Elevator', 386.9, 197.4, 17.0, 0, -11.0, 0.0, 4.0, 0),
            ('US Forward Post', 180.1, 79.9, 15.0, 0, 0.0, 0.0, 0.0, 1),
        ],
    },
    'operationroadrage': {
        'gpm_coop:16': [
            ('Junction Park', 101.5, -103.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hill Crest', 199.8, -165.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Shopping Mall', -187.2, -188.3, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Highway', -27.6, -235.2, 12.0, 0, 0.0, 0.0, 0.0, 1),
        ],
        'gpm_cq:16': [
            ('Ocean Front', 315.5, 129.7, 15.0, 1, 0.0, 0.0, 0.0, 0),
            ('Overpass', -31.1, 54.6, 22.0, 0, 0.0, -10.0, 0.0, 1),
            ('Junction Park', 64.6, -148.3, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Shopping Mall', -187.2, -188.3, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Hill Crest', 217.2, -235.2, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Farm House', -136.1, 824.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Gas Station', -129.0, 399.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Junk Yard', 86.4, 234.8, 17.0, 0, 0.0, 0.0, 0.0, 0),
            ('Overpass', -32.1, 31.9, 15.0, 0, 0.0, 0.0, 0.0, 1),
            ('Shopping Mall', -186.1, -189.7, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Truck Stop', 91.2, -370.1, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Southern Oil Depot', 38.0, -746.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Farm House', -136.2, 823.8, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Gas Station', -129.0, 399.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Junk Yard', 86.3, 234.6, 17.0, 0, 0.0, 0.0, 0.0, 0),
            ('Overpass', -32.1, 31.9, 15.0, 0, 0.0, 0.0, 0.0, 1),
            ('Shopping Mall', -186.1, -189.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Truck Stop', 91.2, -370.1, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Southern Oil Depot', 38.1, -746.1, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Junction Park', 101.5, -103.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hill Crest', 199.8, -165.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Shopping Mall', -187.2, -188.3, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Highway', -27.6, -235.2, 12.0, 0, 0.0, 0.0, 0.0, 1),
        ],
    },
    'operationsmokescreen': {
        'gpm_coop:16': [
            ('North Village', -208.3, 208.3, 15.0, 0, -1.0, 0.0, -3.0, 0),
            ('Oil Storage Facility', -265.4, -87.6, 22.0, 0, 0.0, 0.0, 0.0, 0),
            ('South Village', -110.8, -268.8, 12.0, 0, -3.0, 0.0, -8.0, 0),
            ('Oasis Outpost', 72.4, -521.9, 11.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('North Village', -208.3, 208.3, 15.0, 0, -1.0, 0.0, -3.0, 0),
            ('Oil Storage Facility', -265.4, -87.6, 22.0, 0, 0.0, 0.0, 0.0, 0),
            ('South Village', -110.8, -268.8, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Oasis Outpost', 72.5, -521.9, 11.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Refinery Outpost', 7.3, 430.4, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('North Village', -208.3, 208.3, 15.0, 0, -1.0, 0.0, -3.0, 0),
            ('Hill Shed', 4.4, -29.3, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Oil Storage Facility', -265.4, -87.6, 22.0, 0, 0.0, 0.0, 0.0, 0),
            ('Wind Farm', 152.7, -138.0, 9.0, 0, -3.0, 0.0, -3.0, 0),
            ('South Village', -110.8, -268.7, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Oasis Outpost', 72.5, -521.9, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('North Village', -208.3, 208.3, 15.0, 0, -1.0, 0.0, -3.0, 0),
            ('Oil Storage Facility', -265.4, -87.6, 22.0, 0, 0.0, 0.0, 0.0, 0),
            ('South Village', -110.8, -268.8, 12.0, 0, -3.0, 0.0, -8.0, 0),
            ('Oasis Outpost', 72.4, -521.9, 11.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:32': [
            ('32_US_CP_BASE', 7.4, 430.3, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('32_Neutral_CP_Garage', -211.8, 217.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_Neutral_CP_BurningPlant', -265.4, -87.6, 22.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_Neutral_CP_Windfarm', 148.4, -142.5, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_Neutral_CP_OldVillage', -110.8, -268.7, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('32_MEC_CP_BASE', 72.5, -521.9, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
    },
    'road_to_jalalabad': {
        'gpm_coop:16': [
            ('Mosque', 293.1, 55.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Market', 234.9, -42.1, 16.0, 0, -1.0, 0.0, 1.0, 0),
            ('Hotel', 282.9, -138.2, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Junkyard', 181.6, -170.3, 13.0, 0, -6.5, 0.0, -2.0, 0),
        ],
        'gpm_cq:16': [
            ('Mosque', 293.1, 55.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Market', 234.9, -42.1, 16.0, 0, -1.0, 0.0, 1.0, 0),
            ('Hotel', 282.9, -138.3, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Junkyard', 181.6, -170.3, 13.0, 0, -6.5, 0.0, -2.0, 0),
        ],
        'gpm_cq:32': [
            ('Mosque', 293.1, 55.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('USMC Staging Area', -205.4, 7.7, 20.0, 1, 0.0, 0.0, 0.0, 0),
            ('Market', 234.9, -42.1, 16.0, 0, -1.0, 0.0, 1.0, 0),
            ('Hotel', 282.9, -138.2, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Junkyard', 181.6, -170.3, 13.0, 0, -6.5, 0.0, -2.0, 0),
            ('Outpost', -16.7, -207.8, 20.0, 0, -2.0, 0.0, -3.0, 0),
            ('Fountain', 91.9, -263.2, 20.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Mosque', 293.1, 55.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('USMC Staging Area', -205.4, 7.7, 20.0, 1, 0.0, 0.0, 0.0, 0),
            ('Lake', 38.5, -40.9, 17.0, 0, 3.0, 0.0, 3.0, 0),
            ('Market', 234.9, -42.1, 16.0, 0, -1.0, 0.0, 1.0, 0),
            ('Hotel', 282.9, -138.2, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Junkyard', 181.6, -170.3, 13.0, 0, -6.5, 0.0, -2.0, 0),
            ('Outpost', -16.7, -207.8, 20.0, 0, -2.0, 0.0, -3.0, 0),
            ('Fountain', 91.9, -263.2, 20.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Mosque', 293.1, 55.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Market', 234.9, -42.1, 16.0, 0, -1.0, 0.0, 1.0, 0),
            ('Hotel', 282.9, -138.2, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Junkyard', 181.6, -170.3, 13.0, 0, -6.5, 0.0, -2.0, 0),
        ],
    },
    'sharqi_peninsula': {
        'gpm_coop:16': [
            ('Office Buildings', -188.0, -25.6, 6.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -276.8, -110.6, 3.0, 0, 0.0, 0.0, 0.0, 1),
            ('TV Station', -112.4, -134.4, 10.0, 0, 0.0, 0.0, 0.0, 1),
            ('Hotel', -316.3, -226.3, 9.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('Office Buildings', -188.0, -25.6, 6.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -276.8, -110.6, 3.0, 0, 0.0, 0.0, 0.0, 1),
            ('TV Station', -112.4, -134.4, 10.0, 0, 0.0, 0.0, 0.0, 1),
            ('Hotel', -316.3, -226.3, 9.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Club House', -647.1, 205.1, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('City Entrance', -467.5, -77.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -276.8, -110.6, 6.0, 0, 0.0, 0.0, 0.0, 1),
            ('Surveillance Post', -359.0, -115.0, 6.0, 0, 0.0, 0.0, 0.0, 0),
            ('TV Station', -112.4, -134.4, 10.0, 0, 0.0, 0.0, 0.0, 1),
            ('Outskirts', -605.0, -201.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Hotel', -316.3, -226.3, 9.0, 0, 0.0, 0.0, 0.0, 0),
            ('Beach House', -288.6, -597.2, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Club House', -647.1, 205.1, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Alleyway', -307.6, -25.6, 7.0, 0, 0.0, 0.0, 0.0, 0),
            ('City Entrance', -467.5, -77.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -276.8, -110.6, 6.0, 0, 0.0, 0.0, 0.0, 1),
            ('Surveillance Post', -359.0, -115.0, 6.0, 0, 0.0, 0.0, 0.0, 0),
            ('TV Station', -112.4, -134.4, 10.0, 0, 0.0, 0.0, 0.0, 1),
            ('Outskirts', -605.0, -201.1, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Hotel', -316.3, -226.3, 9.0, 0, 0.0, 0.0, 0.0, 0),
            ('Beach House', -288.6, -597.2, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Office Buildings', -188.0, -25.6, 6.0, 0, 0.0, 0.0, 0.0, 0),
            ('Construction Site', -276.8, -110.6, 3.0, 0, 0.0, 0.0, 0.0, 1),
            ('TV Station', -112.4, -134.4, 10.0, 0, 0.0, 0.0, 0.0, 1),
            ('Hotel', -316.3, -226.3, 9.0, 1, 0.0, 0.0, 0.0, 0),
        ],
    },
    'songhua_stalemate': {
        'gpm_coop:16': [
            ('North Island', -145.4, -91.0, 14.0, 0, 0.0, 0.0, 0.0, 0),
            ('Central Front', -269.0, -175.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('West Perimeter', 113.0, -179.0, 9.0, 0, 0.0, 0.0, 0.0, 0),
            ('Temple', -58.0, -229.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('North Island', -145.4, -91.0, 14.0, 0, 0.0, 0.0, 0.0, 0),
            ('Central Front', -269.0, -175.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('West Perimeter', 113.0, -179.0, 9.0, 0, 0.0, 0.0, 0.0, 0),
            ('Temple', -58.0, -229.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('North Island', -145.4, -91.0, 14.0, 0, 0.0, 0.0, 0.0, 0),
            ('Chinese HQ', -496.8, -127.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Fish Factory', 290.7, -164.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Central Front', -269.0, -175.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('West Perimeter', 113.0, -179.0, 9.0, 0, 0.0, 0.0, 0.0, 0),
            ('South Island', -5.8, -349.3, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('North Perimeter', 201.0, 128.0, 19.0, 0, 0.0, 0.0, 0.0, 0),
            ('North Island', -145.4, -91.0, 14.0, 0, 0.0, 0.0, 0.0, 0),
            ('Chinese HQ', -496.9, -127.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Fish Factory', 290.7, -164.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Central Front', -269.0, -175.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('West Perimeter', 113.0, -179.0, 9.0, 0, 0.0, 0.0, 0.0, 0),
            ('South Island', -5.8, -349.3, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('South Front', -176.0, -442.0, 18.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('North Island', -145.4, -91.0, 14.0, 0, 0.0, 0.0, 0.0, 0),
            ('Central Front', -269.0, -175.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('West Perimeter', 113.0, -179.0, 9.0, 0, 0.0, 0.0, 0.0, 0),
            ('Temple', -58.0, -229.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'strike_at_karkand': {
        'gpm_coop:16': [
            ('Market', -196.0, 183.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Square', -184.8, 97.3, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hotel', -194.4, 11.4, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Gasstation', -161.0, -262.8, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('Market Place', -196.0, 183.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Square', -184.8, 97.3, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hotel', -194.4, 11.4, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Gas Station', -161.0, -262.8, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Gatehouse', 14.0, 289.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Train Accident', -122.4, 256.6, 6.0, 0, 0.0, 0.0, 0.0, 0),
            ('Suburb', -323.8, 220.2, 7.0, 0, 0.0, 0.0, 0.0, 0),
            ('Market', -196.0, 183.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Square', -220.0, 98.1, 7.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hotel', -194.4, 11.3, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Gas Station', -161.0, -262.9, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('Gatehouse', 14.0, 288.9, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Train Accident', -122.4, 256.6, 6.0, 0, 0.0, 0.0, 0.0, 0),
            ('Warehouse', 104.0, 231.1, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Suburb', -323.7, 220.2, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Factory', 183.0, 166.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Cement Factory', 29.4, 164.4, 9.0, 0, 0.0, 0.0, 0.0, 0),
            ('Square', -220.1, 98.1, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hotel', -194.4, 11.4, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Gas Station', -161.0, -262.8, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Market', -196.0, 183.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Square', -184.8, 97.3, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Hotel', -194.4, 11.4, 5.0, 0, 0.0, 0.0, 0.0, 0),
            ('Gasstation', -161.0, -262.8, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
    },
    'taraba_quarry': {
        'gpm_coop:16': [
            ('Farm Community', 18.5, 186.3, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Abandoned Farm House', 245.9, 40.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Engineering Compound', 50.3, -137.4, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('EU Forward Outpost', 297.1, -242.3, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('EU Camp Spearhead', 425.2, -477.1, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('Farm Community', 18.5, 186.3, 5.0, 1, 0.0, 0.0, 0.0, 0),
            ('Abandoned Farm House', 245.9, 40.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Engineering Compound', 50.3, -137.4, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('EU Forward Outpost', 297.1, -242.3, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('EU Camp Spearhead', 425.2, -477.1, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Quarry Dig Site', -154.6, 451.0, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Heavy Equipment Storage', -360.0, 192.1, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Farm Community', 18.5, 186.5, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Freight Railyard', -396.9, -89.5, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Engineering Compound', 159.2, -114.7, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('EU Camp Spearhead', 427.2, -461.5, 15.0, 1, 0.0, 0.0, 0.0, 0),
            ('Taraba Guard HQ', -488.8, -553.2, 15.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Farm Community', 18.5, 186.3, 8.0, 0, 0.0, 0.0, 0.0, 0),
            ('Abandoned Farm House', 245.9, 40.8, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('Engineering Compound', 50.3, -137.4, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('EU Forward Outpost', 297.1, -242.3, 15.0, 0, 0.0, 0.0, 0.0, 0),
            ('EU Camp Spearhead', 425.2, -477.1, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:32': [
            ('Heavy_Equipment_Storage', -575.7, 353.9, 15.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'wake_island_2007': {
        'gpm_cq:64': [
            ('Carrier', -681.2, 694.5, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('North Village', 34.9, 198.8, 30.0, 0, 0.0, 0.0, 0.0, 0),
            ('North Base', 259.2, 184.8, 30.0, 0, 0.0, 0.0, 0.0, 0),
            ('South Base', -28.0, -168.5, 25.0, 0, 0.0, 0.0, 0.0, 0),
            ('Airfield', 359.9, -248.7, 30.0, 0, 0.0, 0.0, 0.0, 0),
            ('Beach', 127.6, -302.4, 20.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
    'zatar_wetlands': {
        'gpm_coop:16': [
            ('Central Island', -53.2, -241.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Factory', -367.4, -330.3, 7.0, 0, 0.0, 0.0, 0.0, 1),
            ('Natural gas Station', 258.6, -352.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:16': [
            ('Central Island', -53.2, -241.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Factory', -367.4, -330.3, 7.0, 0, 0.0, 0.0, 0.0, 1),
            ('Natural Gas Station', 258.6, -352.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:32': [
            ('Airfield', -772.0, 102.0, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Village', -441.1, -59.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Farm', 482.0, -164.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Central Island', -53.2, -241.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Factory', -367.4, -330.2, 7.0, 0, 0.0, 0.0, 0.0, 1),
            ('Natural Gas Station', 258.6, -352.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('MEC Base', 727.0, -401.3, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'gpm_cq:64': [
            ('US Carrier', -432.6, 925.4, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Beach', -565.0, 482.1, 10.0, 1, 0.0, 0.0, 0.0, 0),
            ('Airfield', -772.0, 102.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Village', -441.1, -59.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Farm', 482.0, -164.0, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Central Island', -53.2, -241.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Factory', -367.4, -330.2, 7.0, 0, 0.0, 0.0, 0.0, 1),
            ('Natural Gas Station', 258.6, -352.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('MEC Base', 727.0, -401.3, 10.0, 1, 0.0, 0.0, 0.0, 0),
        ],
        'sp1:16': [
            ('Central Island', -53.2, -241.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
            ('Factory', -367.4, -330.3, 7.0, 0, 0.0, 0.0, 0.0, 1),
            ('Natural gas Station', 258.6, -352.6, 10.0, 0, 0.0, 0.0, 0.0, 0),
        ],
    },
}

# ------------------------------------------------------------------ ModManager interface
# The defaults are the values of the settings above. modmanager.con can override them: mm_claycap_walls.<NAME> <value>
configDefaults = {}
for _k in ['MAPS', 'ZONE_EXTRA', 'MAIN_BASES', 'UNKNOWN_RADIUS', 'REST_TIME', 'CHECK_EVERY', 'SAY', 'MSG_REMOVED',
           'TEST_CHAT', 'LOG_FILE', 'FAN_RULE', 'TRIGGER_RADIUS', 'TRIGGER_ANGLE', 'FACE_OFFSET', 'FACE_MIRROR',
           'UNKNOWN_FACE', 'WALLS', 'BLAST_ANGLE', 'BLAST_REACH', 'SAMPLE_ANGLE', 'SAMPLE_STEP',
           'CHARGE_UP', 'BODY_UP', 'WALL_MS', 'FIRST_LINES', 'FIRST_MS', 'WALL_GIVE_UP', 'LINE_SKIP',
           'NOT_WALLS', 'LOW_LINES', 'LOW_UP', 'LOW_BODY']:
    configDefaults[_k] = globals()[_k]

class ClayCapWalls( object ):

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
        claycap_init()
        try:
            self.mm.info( 'claycap_walls %s is running on mm_flbus (see %s)' % ( VERSION, LOG_FILE or 'no log' ) )
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
    return ClayCapWalls( modManager )
