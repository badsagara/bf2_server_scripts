"""mm_fldm.py - =FL= Deathmatch: a Quake 3 style deathmatch for Battlefield 2.

A ModManager module that runs on the server only; players install nothing.

What it does on a map with an arena (built in: Strike at Karkand, Hotel - Square):
  * team deathmatch (mm_fldm.MODE tdm; off = nothing): the two sides, first side to TEAM_FRAG_LIMIT frags
    wins (free-for-all was taken out in 1.2.7: BF2 has only two sides and bots never shoot a team mate);
  * the arena flags are neutral, so everybody spawns at his base (out of sight) and is dropped at a free arena
    point no enemy looks at, 45-80 m from the nearest enemy where it can (never nearer than 35 m; 25 m after
    4 s of waiting), never within BASE_GAP 25 m of where the game spawned an enemy at his base;
    Karkand has 124 points: 8 built in, 39 marked in the game, 77 picked on the map page (TDM_SPAWN base;
    flag = 1.2.1's spawning by an own flag);
  * headshots only (HEADSHOTS 1, or "fldm hs on" / "!dm hs on"): while deathmatch is on, the game's damage
    table gives 0 to bullets against body, armour, arms and legs, and to knife, explosions and paddles against
    the whole soldier - only a bullet to the head (or helmet) hurts; the game's own values come back after;
  * the flags by layout (LAYOUT_FLAGS): Karkand 16 - the arena flags neutral, everybody spawns at his base;
    32 and 64 - Hotel and the Gas Station US, every other flag MEC; whoever spawns at a flag in the arena is
    dropped at a point too;
    a move goes up, across and down (the game drags a moved soldier along the straight line to the first wall);
  * flags cannot be taken or lowered, no ticket bleed; the tickets show the frags still needed;
  * 1 s spawn protection: health held full;
  * respawn in RESPAWN 1 s (sv.spawnTime, sv.manDownTime and each dead player's time to spawn, only made
    shorter; the server's own values come back when deathmatch is off);
  * the arena border is off by default since 1.2.1 (OUT_ACTION / OUT_BOTS none); with it on: a warning,
    then killed (bots put back);
  * infantry only: a player who gets into a vehicle or onto a gun is told to get out; after VEH_GRACE s
    the vehicle is set to 1 HP when the game allows it, and he is killed when he gets out; frags made from
    vehicles do not count;
  * turned on / off in the middle of a round by an admin: rcon "fldm on" / "fldm off" / "fldm status"
    (BF2CC's console, the game's console after rcon login, or mm_iga chat bindings); until the round ends;
  * Quake style chat: first blood, sprees, Excellent, Humiliation (knife, paddles), lead changes,
    frags left, the winner;
  * every frag: +FRAG_HP 50 health (a supply crate next to the killer: REFILL, off since 1.2.2);
  * pace in the log (PACE): every life from the drop to the death - the nearest enemy at the drop, when an
    enemy first came within 30 m, the first hit taken, the first frag; medians in the round summary.

===== Install =====
  1. Copy mm_fldm.py into admin/modules/ of the server.
  2. In admin/modmanager.con add:  modmanager.loadModule "mm_fldm"
  3. Settings (optional) go under the loadModule lines, e.g.:
       mm_fldm.MODE "tdm"
       mm_fldm.TEAM_FRAG_LIMIT 50
  4. Restart the server. The log is fldm.log in the server's folder.

Python 2.3 (the server's), ASCII only. Sagara / =FL=, 2026-11-14 (1.2.x: 2026-11-15).
"""

import sys
import host
import bf2

try:
    import mm_utils
except Exception:
    mm_utils = None

try:
    import time as _time
except Exception:
    _time = None

__version__ = 1.40
VERSION = '1.4.0'

__required_modules__ = {
    'modmanager': 1.0
}

__supports_reload__ = True

__supported_games__ = {
    'bf2': True,
    'bf2142': False,
    'bfheroes': False,
    'bfp4f': False
}

__description__ = "FL Deathmatch v%s" % VERSION

# ModManager takes unquoted values as whole numbers only, so numbers with a point are strings here.
configDefaults = {
    'MODE': 'tdm',                  # tdm | off
    'TEAM_FRAG_LIMIT': 75,          # frags a side needs to win
    'ARENAS': 'strike_at_karkand: -275 -30 -155 140 Hotel-Square',   # map: x1 z1 x2 z2 [name] | map2: ...
    'POINTS': '',                   # extra arena points: map: x h z yaw, x h z yaw | map2: ...
    'BUILTIN_POINTS': 1,            # 1 = use the 8 built-in Hotel / Square points (Karkand 64 spawn points)
    'MARKED_POINTS': 1,             # 1 = use the 39 points Sagara marked on Karkand (15.11.2026)
    'MAP_POINTS': 1,                # 1 = use the 77 points Sagara picked on the map page (fl_40-fl_119, 15.11.2026)
    'SKIP_POINTS': '',              # point names left out, e.g. "fl_86 fl_70" (built-in and marked ones)
    'BASE_GAP': 25,                 # metres: no drop this close to a place where the game spawned an enemy at
                                    # his base this round (learned from the spawns; 0 = off)
    'OTHER_MAPS': 0,                # 1 = deathmatch rules also on maps without an arena (no moves, no borders)
    'SPAWN_TP': 'auto',             # move spawns to arena points: auto (with TDM_SPAWN base) | all | off
    'TDM_SPAWN': 'base',            # tdm: base (arena flags neutral: spawn at the base, then dropped at a point) |
                                    # flag (1.2.1: FLAG_SIDES / OUTSIDE_FLAGS, spawn by an own arena flag, no moves)
    'SPAWN_SPREAD': 'band',         # band: a free point nobody sees whose nearest enemy is BAND_MIN-BAND_MAX m away
                                    # (random among them; none: the nearest to the band) | random: any free point
                                    # nobody sees | far: the farthest from the enemies (random among SPAWN_PICK best)
    'BAND_MIN': 45,                 # band: metres to the nearest enemy, at least (sprint 6 s, run 12 s)
    'BAND_MAX': 80,                 # ... and at most (sprint 11 s, run 20 s; Karkand's fog hides a man from ~99 m)
    'FLAG_SIDES': 'strike_at_karkand: -194.4 11.4 2 Hotel, -184.8 97.3 1 Square',
                                    # tdm with TDM_SPAWN flag: arena flags given to a side: map: x z side [name], ...
                                    # (the nearest flag within 40 m; Karkand: 1 = MEC, 2 = US) | map2: ...
    'OUTSIDE_FLAGS': 'neutral',     # tdm with TDM_SPAWN flag: flags outside the arena: neutral | keep
                                    # (a side with no flag in the arena keeps its own)
    'LAYOUT': 'auto',               # the map's layout size: auto (from the server's map list, else by the number
                                    # of flags) | 16 | 32 | 64
    'LAYOUT_FLAGS': ('strike_at_karkand: 16 = hotel us, square mec; 32 = hotel us, gasstation us, other mec; '
                     '64 = hotel us, gasstation us, other mec'),
                                    # the flags' sides by layout: "map: size = flag side, ..., other side; size = ...
                                    # | map2: ..." (flag: part of its name, e.g. hotel; side us | mec | neutral |
                                    # keep; other: keep when not given). A layout not given keeps the arena flags
                                    # neutral (as NEUTRAL_ARENA). Everybody spawning at a flag in the arena is
                                    # dropped too. Karkand 16 since 1.3.4: Hotel US, Square MEC, the bases kept.
    'NEUTRAL_ARENA': 1,             # tdm base: flags inside the arena made neutral (everybody spawns outside,
                                    # then moved); a side keeps one if it has none outside
    'LOCK_FLAGS': 1,                # flags cannot be taken: the flag templates get unableToChangeTeam 1, and every
                                    # 0.1 s the side, the flag and a lowering flag are put back
    'FLAG_RAISE': '1.0',            # a flag being lowered is raised again at this speed (1.0 = the whole pole in 1 s)
    'SPAWN_PICK': 3,                # random among this many best points (unseen first, then farthest)
    'SPAWN_RECENT': '3.0',          # a point used this many seconds ago is not used again
    'TP_CLEAR': '2.5',              # a point with a living soldier this close (across the ground) is taken
    'TP_ENEMY_MIN': 35,             # a point with a living enemy this close (across the ground) is not taken
    'TP_ENEMY_LOW': 25,             # ... after TP_WAIT s of waiting this close will do (many players, few points)
    'TP_WAIT': '4.0',               # seconds a spawn waits for a fresh point; then one used lately (but empty) will do
    'TP_GIVE_UP': '15.0',           # seconds after which a spawn that found no empty point is left where he is
    'SEE_NEAR': 15,                 # an enemy this close sees a point whatever way he looks
    'SEE_FAR': 80,                  # ... and this close inside his view cone (Karkand's fog ends ~99 m)
    'SEE_CONE': 60,                 # half the view cone, degrees from where he faces
    'TP_ROUTE': 'sky',              # sky: up, across, down, a step a tick | direct (the game drags a moved soldier
                                    # along the straight line and stops him at the first wall: 15.11 test)
    'TP_SKY': 60,                   # metres over the higher of the two places
    'TP_STEP': '0.05',              # seconds between the steps of the sky route (under 0.1: a timer of its own;
                                    # 0.1 before 1.3.7)
    'TP_UP': '1.4',                 # metres over the point (a soldier's place reads ~1.0 m over the ground)
    'TP_OK': '4.0',                 # metres off the point (across the ground) that still count as moved
    'TP_BAD': '8.0',                # metres off that count as a miss; a point with 2 misses is left out for the round
    'TP_PER_TICK': 2,               # spawns given a point in one 0.1 s tick at most (the rest wait a tick)
    'TP_DELAY': '0.4',              # seconds after the spawn (the game puts the soldier on his spawn point first;
                                    # 0.8 before 1.3.7 - if drops "land off" more often, put it back up)
    'SPAWN_GUARD': '1.0',           # seconds after a spawn (or a move) when health is held full; 0 = off
    'GUARD_ENDS_ON_FRAG': 1,        # the protection ends when he frags somebody
    'SPAWN_LOG': 20,                # spawns a round logged with the nearest enemy
    'PACE': 1,                      # 1 = pace in the log: every life from the drop (or the spawn) to the death -
                                    # the nearest enemy then, the first hit taken, the first frag, the first enemy
                                    # within PACE_NEAR m; the round summary has the medians
    'PACE_NEAR': 30,                # metres: an enemy this close counts as met (0 = not watched: fewer calls)
    'PACE_LOG': 300,                # lives a round logged one by one (the summary counts them all)
    'OUT_TIME': 5,                  # seconds outside the arena before the action
    'OUT_ACTION': 'none',           # people outside the arena: none (no border, since 1.2.1) | kill | tp
    'OUT_BOTS': 'none',             # bots outside: none | kill | tp
    'OUT_GRACE': '2.0',             # seconds after a spawn when the border is not checked
    'ARENA_EVERY': '1.0',           # seconds between border checks
    'HEADSHOTS': 0,                 # 1 = only a bullet to the head kills while deathmatch is on: the game's damage
                                    # table (MaterialManager) gets 0 for bullets against body, armour, arms and
                                    # legs, and for knife, explosions and paddles against the whole soldier; the
                                    # server's own values come back when deathmatch is off
    'HS_HEAD': 0,                   # with HEADSHOTS: bullets against the head x this (the game's: small arms 3,
                                    # .50 cal 1.5); 0 = leave the game's (10 = any headshot kills at once)
    'HS_PER_TICK': 20,              # damage cells changed in one 0.1 s tick (142 in all)
    'GRENADES': 0,                  # 0 (default since 1.3.8) = hand grenades and grenade launchers do not hurt
                                    # soldiers while deathmatch is on: damage cells of Grenade_hand 46, Grenade_rifle
                                    # 45 and their blast Detonation_grenade 69, and (1.3.8) their projectiles'
                                    # detonation.explosionDamage and damage 0 (GRENADE_NAMES); 1 = as in the game
    'GRENADE_NAMES': 'ushgr_m67, usrgl_m203, rurgl_gp30, rurgl_gp25, chhgr_type82',
    'KNIVES': 1,                    # 0 = the knife does not hurt (Knife 48)
    'ROCKETS': 1,                   # 0 = AT rockets (SRAW, Eryx) do not hurt soldiers (Missile_antitank 52, their
                                    # blast Explosion_blastwave 70 - tank and APC shell blasts may use it too)
    'DEFIBS': 1,                    # 0 = the defibrillator paddles do not hurt (Soldier_resurrection 89); reviving
                                    # is not a damage cell and should still work (to be checked)
    'SNIPERS': 0,                   # 0 = sniper rifles do no damage while deathmatch is on: their projectiles get
                                    # ObjectTemplate.damage 0 (read first, put back after), a sniper kill does not
                                    # count, a player who takes one out is told; 1 = as in the game
    'SNIPER_NAMES': 'usrif_m24, rurif_dragunov, chsni_type88, ussni_m95_barret, gbrif_l96a1',
                                    # the sniper rifles (a name the server does not have is left alone)
    'STATIONARY': 0,                # 0 = stationary MGs (mec_bipod, us_bipod) do no damage while deathmatch is on,
                                    # the same way as SNIPERS; 1 = they shoot as in the game AND may be used
                                    # (NO_VEHICLES leaves a stationary MG alone, its frags count)
    'STATIONARY_NAMES': 'rulmg_rpk74_stationary, uslmg_m249saw_stationary',
                                    # the stationary MGs' guns
    'VEHICLE_MG': 0,                # 0 = the jeeps' MGs (HMMWV M2, Vodnik Kord) do no damage; 1 = they shoot and the
                                    # gunner's seat may be used (the driver still gets the NO_VEHICLES rule)
    'VEHICLE_MG_NAMES': 'hmg_m2hb, chhmg_kord',
                                    # the vehicle MGs' guns
                                    # !dm hs | nades | knife | rockets | defib | snipers on|off (or rcon "fldm ...")
                                    # change HEADSHOTS, GRENADES, KNIVES, ROCKETS, DEFIBS, SNIPERS until the server
                                    # restarts (modmanager.con unchanged)
    'RESPAWN': 1,                   # seconds: sv.spawnTime and each dead player's time to spawn while deathmatch
                                    # is on (only made shorter; the server's own comes back after); 0 = leave it
    'MAN_DOWN': 1,                  # sv.manDownTime the same way; 0 = leave it
    'NO_VEHICLES': 1,
    'VEH_GRACE': 3,                 # seconds to get out of a vehicle
    'VEH_HP': 1,                    # health given to a vehicle that is not left
    'FRAG_HP': 50,                  # health for a frag (on foot), up to HP_MAX; 100 = full, 0 = off (50 since 1.3.6)
    'REFILL': 'off',                # crate: a supply crate next to the killer for REFILL_LIFE s every frag | off
                                    # (off since 1.2.2: Object.delete does not take a crate away on the server)
    'REFILL_LIFE': '1.0',
    'REFILL_OFFSET': '1.5',         # metres from the killer
    'REFILL_DELETE': 1,             # take the crate away with Object.delete; one that stays is parked in the sky
                                    # and used again for the next frag
    'REFILL_SKY': 300,              # metres up for a parked crate (lifted again while it falls)
    'REFILL_MAX': 12,               # most crates at once (the oldest go first)
    'REFILL_LOG': 3,                # crates a round logged in detail
    'ARENA_CRATES': 10,             # supply crates (CRATE) spread over the arena's points while deathmatch is on;
                                    # 0 = none (most 30)
    'ARENA_CRATE_EVERY': 60,        # seconds: then they all move to new points (spread out, not the last ones)
    'ARENA_CRATE_HEAL': 0,          # the crate template's healSpeed while they are out (0 = ammo only)
    'ARENA_CRATE_AMMO': '',         # its refillAmmoSpeed then ('' = the game's own; 1000 = at once)
    'ARENA_CRATE_MODE': 'new',      # new: every move makes new crates and puts the old ones away (a crate made
                                    # while you play is surely sent to your game) | move: the same crates moved
    'ARENA_CRATE_START': 20,        # seconds after deathmatch starts before the first crates (people loading in)
    'ARENA_CRATE_WAY': 'spawner',   # spawner: a crate is made by our own ObjectSpawner (the game makes it - the way
                                    # the claytest crate was seen) | direct: Object.create supply_crate (1.3.7-1.3.9:
                                    # the server had them, the players did not see them)
    'ARENA_CRATE_DROP': 40,         # metres over its point a crate is made: it comes down on its own parachute
                                    # (supply_crate carries supply_parachute), like the commander's; 0 = on the ground
    'INF_MAGS': 0,                  # off since 1.2.0: the server takes the number, the game does not (15.11 test)
    'MAGS': 99,                     # at most 500: the game sends magazines in 9 bits (999 crashed the server)
    'INF_SKIP': 'hgr mine claymore c4_ atp_ eryx predator tow hj8 rgl gr_ knife kni_ defib medikit ammokit wrench',
    'INF_NAMES': '',                # gun templates to change at once at a round start (exact names, comma list)
    'HP_MAX': 100,
    'HP_NUDGE': 1,                  # 1 = one point less first, then the health, so the screen shows it
    'DROP_MODE': 'off',             # bags | crate | spawner | off (off since 1.1.0: full heal a frag instead)
    'DROP_MED': 3,
    'DROP_AMMO': 3,
    'MED_BAG': 'medikit_Projectile',
    'AMMO_BAG': 'ammokit_Projectile',
    'CRATE': 'supply_crate',
    'CRATE_FAST': 1,                # crates refill and heal at once (refillAmmoSpeed 1000, healSpeed 100)
    'DROP_RADIUS': '1.0',           # metres round the body
    'DROP_UP': '0.4',               # metres over the body's place
    'DROP_LIFE': 25,                # seconds before a dropped item still lying is taken away
    'DROP_MAX': 90,                 # most dropped items at once (the oldest go first)
    'DROP_TEAM': 'killer',          # killer | victim | none : Object.team of the dropped items
    'DROP_OUTSIDE': 0,              # 1 = drop also when the soldier died outside the arena
    'DROP_LOG': 2,                  # drops a round logged in detail (console answers, checks 1 s and 3 s later)
    'ANNOUNCE': 1,                  # first blood, sprees, excellent, humiliation, lead, frags left
    'SPREE': 5,                     # a spree line every this many frags without dying
    'EXCELLENT': '2.0',             # two frags within this many seconds
    'LEFT_WARN': '5 3 1',           # frags left to say
    'RULES_DELAY': 15,              # seconds after the round start for the rules line
    'RULES_EVERY': 300,             # seconds between rules lines, 0 = once
    'END_DELAY': 3,                 # seconds between the winner line and the round's end
    'SCORE_IS_FRAGS': 1,            # scoreboard: score = frags, kills = frag kills
    'HOLD_TICKETS': 1,
    'NO_ARTY_FRAGS': 1,             # artillery kills give no frag
    'PUBLIC_SCORE': 1,              # !dm (the score) and !dm info (weapons, spawn distance) for everybody
    'TEST_COMMANDS': 0,             # !dm drop / scan / here / tp / points / mode / limit / end / where
    'TEST_CHAT': 0,                 # more lines in the chat for tests
    'CHAT_MAX': 180,
    'LAG_GAP': '0.35',              # seconds between two 0.1 s ticks logged as a server stall
    'LAG_LOG': 10,                  # stalls (and slow ticks of this script) a round logged in detail
    'LOG_FILE': 'fldm.log'
}

CP_TYPE = 'dice.hfe.world.ObjectTemplate.ControlPoint'
PROJ_TYPE = 'dice.hfe.world.ObjectTemplate.GenericProjectile'
SUPPLY_TYPE = 'dice.hfe.world.ObjectTemplate.SupplyObject'

# Karkand 64 conquest spawn points of Hotel and Square (GamePlayObjects.con; hotel_4 = hotel_3; hotel_5 +1.25);
# the last number is the side the point is for in tdm (2 = US at the Hotel, 1 = MEC at the Square, 0 = any)
BUILTIN = {
    'strike_at_karkand': [
        ('hotel_1', -189.80, 155.90, 26.38, -104.1, 2),
        ('hotel_2', -222.87, 155.90, -3.19, 90.0, 2),
        ('hotel_3', -189.34, 155.90, 0.62, -90.0, 2),
        ('hotel_5', -222.77, 157.15, 14.73, 90.0, 2),
        ('square_1', -244.96, 155.90, 123.39, 178.663, 1),
        ('square_2', -206.03, 155.90, 106.99, -88.901, 1),
        ('square_3', -251.06, 155.90, 82.85, 90.0, 1),
        ('square_4', -247.86, 155.90, 104.55, 90.0, 1)
    ]
}

# Points marked by Sagara with !dm here on the test server, 15.11.2026 (any side; heights = the ground)
MARKED = {
    'strike_at_karkand': [
        ('fl_01', -179.73, 164.21, 43.05, 153, 0),
        ('fl_02', -177.71, 164.19, 34.41, -7, 0),
        ('fl_03', -146.21, 155.90, 49.14, 87, 0),
        ('fl_04', -130.17, 155.80, 56.90, -102, 0),
        ('fl_05', -146.30, 163.85, 60.32, -168, 0),
        ('fl_06', -140.45, 164.00, 44.79, 7, 0),
        ('fl_07', -147.91, 155.90, 86.86, 18, 0),
        ('fl_08', -133.59, 155.80, 97.88, 4, 0),
        ('fl_09', -150.39, 153.26, 121.07, 178, 0),
        ('fl_10', -179.76, 153.51, 112.26, -97, 0),
        ('fl_11', -214.04, 149.90, 112.70, -88, 0),
        ('fl_12', -222.21, 149.90, 120.41, -6, 0),
        ('fl_13', -215.11, 156.81, 153.47, 178, 0),
        ('fl_14', -246.88, 155.80, 171.12, -97, 0),
        ('fl_15', -273.78, 155.80, 173.47, -90, 0),
        ('fl_16', -259.18, 166.25, 165.13, 168, 0),
        ('fl_17', -271.32, 167.64, 164.65, -114, 0),
        ('fl_18', -287.87, 156.08, 134.27, -143, 0),
        ('fl_19', -258.44, 155.90, 134.26, 149, 0),
        ('fl_20', -251.32, 160.52, 128.47, 43, 0),
        ('fl_21', -260.47, 155.90, 103.25, 174, 0),
        ('fl_22', -285.16, 155.90, 91.75, 102, 0),
        ('fl_23', -261.41, 155.90, 58.97, 7, 0),
        ('fl_24', -281.36, 155.90, 42.43, 86, 0),
        ('fl_25', -268.64, 155.90, 35.87, 76, 0),
        ('fl_26', -230.43, 155.90, 30.28, 148, 0),
        ('fl_27', -248.91, 155.80, 14.73, 10, 0),
        ('fl_28', -161.03, 155.90, 48.85, 178, 0),
        ('fl_29', -171.00, 155.90, 26.64, -92, 0),
        ('fl_30', -173.99, 155.90, 0.75, -91, 0),
        ('fl_31', -182.06, 155.90, -4.90, -180, 0),
        ('fl_32', -186.22, 160.52, -9.21, -52, 0),
        ('fl_33', -208.88, 155.90, 106.56, -96, 0),
        ('fl_34', -222.40, 155.80, 105.72, 177, 0),
        ('fl_35', -226.47, 155.80, 86.17, -126, 0),
        ('fl_36', -182.70, 154.78, 93.31, -118, 0),
        ('fl_37', -207.99, 168.77, 88.72, 42, 0),
        ('fl_38', -212.61, 170.32, 94.26, -13, 0),
        ('fl_39', -206.68, 173.12, 99.72, 97, 0)
    ]
}

# Points Sagara picked on the map page (Karkand geometry: the ground or roof under each, the facing worked out
# from the map), 15.11.2026; any side. 77 of his 80: the three highest roofs are out (Sagara, 15.11 15:03) -
# fl_70 (20 m), fl_86 (28 m, the hotel's top), fl_111 (20 m). Roofs higher than 10 m still in: fl_69, fl_81,
# fl_87, fl_100.
MAP_PICKED = {
    'strike_at_karkand': [
        ('fl_40', -190.30, 151.40, 127.10, -30, 0),
        ('fl_41', -132.00, 149.80, 124.60, 0, 0),
        ('fl_42', -139.90, 155.80, 78.40, 15, 0),
        ('fl_43', -155.20, 155.80, 71.40, -90, 0),
        ('fl_44', -185.20, 155.80, 72.50, -15, 0),
        ('fl_45', -204.20, 155.80, 53.90, 15, 0),
        ('fl_46', -236.90, 155.80, 45.10, -90, 0),
        ('fl_47', -236.90, 155.80, 74.10, 90, 0),
        ('fl_48', -139.70, 149.80, 121.00, 15, 0),
        ('fl_49', -131.90, 149.80, 141.20, -90, 0),
        ('fl_50', -133.80, 149.80, 167.20, 180, 0),
        ('fl_51', -170.60, 149.80, 165.00, 75, 0),
        ('fl_52', -169.20, 149.80, 145.40, -105, 0),
        ('fl_53', -201.70, 149.80, 172.80, 180, 0),
        ('fl_54', -205.10, 149.80, 140.10, 90, 0),
        ('fl_55', -216.40, 149.80, 173.90, 150, 0),
        ('fl_56', -216.70, 157.00, 127.30, 180, 0),
        ('fl_57', -229.50, 155.80, 157.60, 180, 0),
        ('fl_58', -239.00, 155.80, 178.90, 150, 0),
        ('fl_59', -269.20, 162.00, 186.30, 120, 0),
        ('fl_60', -282.50, 161.80, 183.20, 105, 0),
        ('fl_61', -283.70, 155.80, 162.70, 165, 0),
        ('fl_62', -295.10, 155.80, 141.90, 120, 0),
        ('fl_63', -298.90, 161.60, 180.60, 150, 0),
        ('fl_64', -297.20, 157.60, 158.40, 105, 0),
        ('fl_65', -299.70, 155.80, 115.50, 90, 0),
        ('fl_66', -266.50, 155.80, 112.40, 90, 0),
        ('fl_67', -268.70, 155.80, 134.50, 180, 0),
        ('fl_68', -254.20, 160.90, 95.30, 120, 0),
        ('fl_69', -253.70, 166.60, 63.80, 75, 0),
        ('fl_71', -305.10, 158.30, 78.00, 90, 0),
        ('fl_72', -291.70, 155.80, 46.90, 0, 0),
        ('fl_73', -290.10, 155.80, 24.40, 135, 0),
        ('fl_74', -286.00, 155.80, 4.10, 135, 0),
        ('fl_75', -272.20, 155.80, 9.20, 150, 0),
        ('fl_76', -251.90, 155.80, 1.10, -60, 0),
        ('fl_77', -253.10, 155.70, -17.40, -45, 0),
        ('fl_78', -240.10, 155.80, -34.80, 0, 0),
        ('fl_79', -220.20, 160.90, -35.20, -45, 0),
        ('fl_80', -223.70, 161.10, -15.90, -60, 0),
        ('fl_81', -224.10, 167.90, 4.50, -30, 0),
        ('fl_82', -188.60, 155.80, -31.70, -45, 0),
        ('fl_83', -171.40, 161.10, -31.70, -90, 0),
        ('fl_84', -170.70, 160.70, -14.70, 60, 0),
        ('fl_85', -173.20, 162.90, -6.20, 75, 0),
        ('fl_87', -147.70, 170.50, -34.20, -60, 0),
        ('fl_88', -134.20, 155.80, -14.80, 0, 0),
        ('fl_89', -132.20, 155.80, -3.00, 0, 0),
        ('fl_90', -130.40, 155.80, 15.30, 0, 0),
        ('fl_91', -147.00, 160.70, -2.50, -120, 0),
        ('fl_92', -131.70, 156.60, 30.80, 0, 0),
        ('fl_93', -130.90, 155.80, 44.60, 0, 0),
        ('fl_94', -147.10, 163.00, 20.60, -75, 0),
        ('fl_95', -133.10, 155.80, 67.70, 0, 0),
        ('fl_96', -119.90, 149.90, 117.60, 180, 0),
        ('fl_97', -120.40, 149.90, 96.10, 180, 0),
        ('fl_98', -160.60, 155.80, 81.20, -90, 0),
        ('fl_99', -160.50, 155.80, 100.20, -75, 0),
        ('fl_100', -189.80, 166.70, 36.30, 15, 0),
        ('fl_101', -196.50, 158.40, 10.70, -30, 0),
        ('fl_102', -198.80, 155.80, -35.20, -15, 0),
        ('fl_103', -210.10, 155.80, -24.10, 0, 0),
        ('fl_104', -203.00, 155.80, 0.50, -15, 0),
        ('fl_105', -209.80, 155.80, 24.40, 0, 0),
        ('fl_106', -213.60, 155.80, 54.60, 45, 0),
        ('fl_107', -252.10, 155.80, 46.40, 90, 0),
        ('fl_108', -271.20, 155.80, 48.70, 0, 0),
        ('fl_109', -275.10, 155.80, 81.60, 165, 0),
        ('fl_110', -271.20, 155.80, 146.50, 180, 0),
        ('fl_112', -249.30, 155.80, 187.90, 135, 0),
        ('fl_113', -186.00, 157.90, 157.10, -150, 0),
        ('fl_114', -150.10, 149.80, 173.80, -135, 0),
        ('fl_115', -133.60, 149.80, 187.80, -135, 0),
        ('fl_116', -199.70, 149.80, 191.70, 180, 0),
        ('fl_117', -199.20, 149.80, 119.90, -15, 0),
        ('fl_118', -191.80, 155.50, 83.00, -15, 0),
        ('fl_119', -210.30, 155.80, 71.70, 45, 0)
    ]
}

# HEADSHOTS: damage cells (attack material, soldier material, the game's own damageMod) from BF2 1.5's
# Common_server.zip Material/materialManagerSettings.con (25.11.2026; a cell the file does not set counts 1.0).
# Soldier materials: 23 Human_bodyarmour, 24 Human_body, 25 Human_head, 77 Human_limbs, 1010 Penetrable_Helmet.
# Bullets (38 small arms, 39 .50 cal, 40 minigun, 41 shotgun) against 23 / 24 / 77; knife 48, grenades, shells,
# missiles, mines, claymore, C4, blast waves, empty shells, paddles 89 against all five. Left alone: healing 73,
# repair 84, ammo 91, falls and collisions (ground and object materials), Death_material 666.
# 1.4.0: with headshots only, knives (48), paddles (89) and AT rockets (52, their blast 70) still kill anywhere.
HS_KEEP = (48, 89, 52, 70)
HS_CELLS = [
    (38, 23, 0.66), (38, 24, 1.0), (38, 77, 0.7), (39, 23, 1.0), (39, 24, 1.0), (39, 77, 0.325),
    (40, 23, 0.5), (40, 24, 1.0), (40, 77, 0.5), (41, 23, 0.52), (41, 24, 1.0), (41, 77, 0.7),
    (42, 23, 1.75), (42, 24, 1.75), (42, 25, 1.75), (42, 77, 1.0), (42, 1010, 1.0), (43, 23, 1.0),
    (43, 24, 1.0), (43, 25, 1.0), (43, 77, 1.0), (43, 1010, 1.0), (44, 23, 1.0), (44, 24, 1.0),
    (44, 25, 1.0), (44, 77, 1.0), (44, 1010, 1.0), (45, 23, 1.0), (45, 24, 1.0), (45, 25, 1.0),
    (45, 77, 0.0), (45, 1010, 1.0), (46, 23, 0.0), (46, 24, 0.0), (46, 25, 0.0), (46, 77, 175.0),
    (46, 1010, 1.0), (47, 23, 1.0), (47, 24, 1.0), (47, 25, 1.0), (47, 77, 1.0), (47, 1010, 1.0),
    (48, 23, 5.0), (48, 24, 5.0), (48, 25, 5.0), (48, 77, 5.0), (48, 1010, 1.0), (49, 23, 1.0),
    (49, 24, 1.0), (49, 25, 1.0), (49, 77, 1.0), (49, 1010, 1.0), (50, 23, 1.0), (50, 24, 1.0),
    (50, 25, 1.0), (50, 77, 1.0), (50, 1010, 1.0), (52, 23, 1.0), (52, 24, 1.0), (52, 25, 1.0),
    (52, 77, 1.0), (52, 1010, 1.0), (53, 23, 1.0), (53, 24, 1.0), (53, 25, 1.0), (53, 77, 1.0),
    (53, 1010, 1.0), (55, 23, 1.0), (55, 24, 1.0), (55, 25, 1.0), (55, 77, 1.0), (55, 1010, 1.0),
    (56, 23, 1.75), (56, 24, 1.75), (56, 25, 1.75), (56, 77, 1.5), (56, 1010, 1.0), (57, 23, 4.0),
    (57, 24, 4.0), (57, 25, 6.0), (57, 77, 1.0), (57, 1010, 1.0), (63, 23, 1.0), (63, 24, 1.0),
    (63, 25, 1.0), (63, 77, 1.0), (63, 1010, 1.0), (65, 23, 1.0), (65, 24, 1.0), (65, 25, 1.0),
    (65, 77, 1.0), (65, 1010, 1.0), (69, 23, 1.0), (69, 24, 1.0), (69, 25, 1.0), (69, 77, 1.0),
    (69, 1010, 1.0), (70, 23, 1.75), (70, 24, 1.75), (70, 25, 1.75), (70, 77, 1.0), (70, 1010, 1.0),
    (80, 23, 0.2), (80, 24, 0.2), (80, 25, 0.2), (80, 77, 1.0), (80, 1010, 1.0), (87, 23, 1.5),
    (87, 24, 1.5), (87, 25, 1.5), (87, 77, 1.0), (87, 1010, 1.0), (88, 23, 4.0), (88, 24, 4.0),
    (88, 25, 6.0), (88, 77, 1.0), (88, 1010, 1.0), (89, 23, 1.0), (89, 24, 1.0), (89, 25, 1.0),
    (89, 77, 1.0), (89, 1010, 1.0), (92, 23, 1.0), (92, 24, 1.0), (92, 25, 1.0), (92, 77, 1.0),
    (92, 1010, 1.0), (104, 23, 1.0), (104, 24, 1.0), (104, 25, 1.0), (104, 77, 1.0), (104, 1010, 1.0),
    (109, 23, 2.0), (109, 24, 2.0), (109, 25, 2.0), (109, 77, 1.0), (109, 1010, 1.0), (113, 23, 1.5),
    (113, 24, 1.5), (113, 25, 1.5), (113, 77, 1.0), (113, 1010, 1.0)
]
HS_HEADS = [(38, 25, 3.0), (39, 25, 1.5), (40, 25, 3.0), (41, 25, 3.0)]
MATERIAL_NAMES = {23: 'Human_bodyarmour', 24: 'Human_body', 25: 'Human_head', 77: 'Human_limbs',
                  1010: 'Penetrable_Helmet', 38: 'Bullet_small_arms', 39: 'Bullet_50caliber', 40: 'Bullet_minigun',
                  41: 'Bullet_shotgun', 45: 'Grenade_rifle', 46: 'Grenade_hand', 48: 'Knife', 52: 'Missile_antitank',
                  69: 'Detonation_grenade', 70: 'Explosion_blastwave', 80: 'Detonation_C4'}
SOLDIER_MATS = (23, 24, 25, 77, 1010)
USAGE = ('fldm: on | off | status | info [say] | hp [0-100|full|off] | crates [0-30|off|now] | hs [on|off] | nades [on|off] | knife [on|off] | rockets [on|off] | '
         'defib [on|off] | snipers [on|off] | stationary [on|off] | vehmg [on|off] | weapons | '
         'band [min max [never under]]')
# GRENADES / KNIVES / ROCKETS 0: the attack materials whose cells against SOLDIER_MATS go to 0. From the weapon
# templates (25.11.2026): hand grenade ushgr_m67 material 46, blast 69; grenade launchers material 46 (or 45),
# blast 69 too, so they go with the grenades; knife 48; AT missiles at_predator and eryx material 52, blast 70.
# (key, setting, name for the log and the chat, attack materials, bits of kill weapon names)
WEAPON_GROUPS = [
    ('nades', 'GRENADES', 'grenades', (45, 46, 69), ('hgr_', 'rgl_', 'grenade')),
    ('knife', 'KNIVES', 'knives', (48,), ('kni_', 'knife')),
    ('rockets', 'ROCKETS', 'rockets', (52, 70), ('atp_', 'eryx', 'rpg', 'predator')),
    ('defib', 'DEFIBS', 'defibrillators', (89,), ('defib',))
]
WEAPON_WORDS = {'nades': 'nades', 'nade': 'nades', 'grenades': 'nades', 'grenade': 'nades', 'gren': 'nades',
                'knife': 'knife', 'knives': 'knife', 'rockets': 'rockets', 'rocket': 'rockets', 'rpg': 'rockets',
                'at': 'rockets', 'defib': 'defib', 'defibs': 'defib', 'defibrillator': 'defib',
                'defibrillators': 'defib', 'paddles': 'defib'}
# guns made harmless by ObjectTemplate.damage 0 on their projectiles: (key, setting, names setting, name for the
# chat, bits of kill weapon names, the bullet materials allowed, name for the log, unit, one of them)
# (... , the property that tells it is the right template, the properties set to 0 (property, must be over 0),
# 1 = switched with a WEAPON_GROUPS switch and not shown on its own)
BULLET = ('material', [('damage', 1)], 0)
TZ_GROUPS = [
    ('snipers', 'SNIPERS', 'SNIPER_NAMES', 'sniper rifles', ('sni_',), ('38', '39'), 'snipers', 'rifles',
     'a sniper rifle') + BULLET,
    ('stationary', 'STATIONARY', 'STATIONARY_NAMES', 'stationary MGs', ('_stationary',), ('38', '39', '40'),
     'stationary MGs', 'guns', 'a stationary MG') + BULLET,
    ('vehmg', 'VEHICLE_MG', 'VEHICLE_MG_NAMES', 'vehicle MGs', ('hmg_',), ('38', '39', '40'), 'vehicle MGs', 'guns',
     'a vehicle MG') + BULLET,
    ('nades', 'GRENADES', 'GRENADE_NAMES', 'grenades', ('hgr_', 'rgl_'), ('69',), 'grenades', 'grenades',
     'a grenade', 'detonation.explosionMaterial', [('detonation.explosionDamage', 1), ('damage', 0)], 1)
]
PROP_WORDS = {'material': 'material', 'damage': 'damage', 'detonation.explosionMaterial': 'explosion material',
              'detonation.explosionDamage': 'explosionDamage'}
TZ_WORDS = {'snipers': 'snipers', 'sniper': 'snipers', 'sni': 'snipers', 'snipe': 'snipers',
            'stationary': 'stationary', 'statmg': 'stationary', 'bipod': 'stationary', 'stmg': 'stationary',
            'vehmg': 'vehmg', 'carmg': 'vehmg', 'jeepmg': 'vehmg', 'vmg': 'vehmg'}
SNIPER_WORDS = ('snipers', 'sniper', 'sni', 'snipe')
STATIONARY_ROOTS = ('bipod',)       # a vehicle root with this in its name is a stationary MG
GUNNER_SEATS = ('cupola',)          # a seat with this in its name is a jeep's MG (USJEP_HMMWV_CupolaBase)
# weapons whose projectile materials are read back and logged once a server run (a check of the table above)
WEAPON_PROBE = ['ushgr_m67', 'usrgl_m203', 'rurgl_gp30', 'kni_knife', 'usatp_predator', 'chat_eryx', 'defibrillator']


def dmg_default_table():
    t = {}
    for c in HS_CELLS + HS_HEADS:
        t[(c[0], c[1])] = c[2]
    return t
DMG_DEFAULT = dmg_default_table()


def key_ok(pt):
    return pt and not pt.startswith('ERROR') and ' ' not in pt

# Where a map's flags stand, for LAYOUT_FLAGS when a flag's name does not tell (x, z; every layout).
KNOWN_FLAGS = {
    'strike_at_karkand': [('hotel', -194.4, 11.4), ('gasstation', -161.0, -262.8), ('square', -184.8, 97.3),
                          ('square', -220.0, 98.0), ('market', -196.0, 183.6), ('suburb', -324.0, 220.0),
                          ('trainaccident', -122.0, 257.0), ('gatehouse', 14.0, 289.0), ('warehouse', 104.0, 231.0),
                          ('cementfactory', 29.0, 164.0), ('factory', 183.0, 166.0)]
}


def fmt_num(v):
    """0 -> '0', 0.66 -> '0.66', 3.0 -> '3' (for console commands)."""
    t = '%.4f' % float(v)
    t = t.rstrip('0').rstrip('.')
    if t in ('', '-0'):
        t = '0'
    return t


def parse_layout_flags(text):
    """'map: 32 = hotel us, other mec; 64 = ... | map2: ...' -> {map: {size: [(name, side word)]}}"""
    res = {}
    for part in str(text).split('|'):
        if ':' not in part:
            continue
        (mp, rest) = part.split(':', 1)
        mp = mp.strip().lower()
        for item in rest.split(';'):
            if '=' not in item:
                continue
            (sz, lst) = item.split('=', 1)
            try:
                sz = int(sz.strip())
            except Exception:
                continue
            rows = []
            for e in lst.split(','):
                w = e.split()
                if len(w) >= 2:
                    rows.append((''.join(w[:-1]).lower().replace('_', ''), w[-1].lower()))
            res.setdefault(mp, {})[sz] = rows
    return res


# Points taken out again (Sagara, 15.11 15:03: the highest roofs). The same spot given in a POINTS line is left
# out too (so an old POINTS line with the 80 does not bring them back).
TAKEN_OUT = {
    'strike_at_karkand': [('fl_70', -285.9, 65.1), ('fl_86', -179.2, 11.8), ('fl_111', -245.4, 163.1)]
}

# 12 directions, 30 degrees apart (x east, z north), for the dropped items
DIRS = [(0.0, 1.0), (0.5, 0.866), (0.866, 0.5), (1.0, 0.0), (0.866, -0.5), (0.5, -0.866),
        (0.0, -1.0), (-0.5, -0.866), (-0.866, -0.5), (-1.0, 0.0), (-0.866, 0.5), (-0.5, 0.866)]

SPREE_WORDS = [(25, 'is godlike'), (20, 'is unstoppable'), (15, 'is dominating'),
               (10, 'is on a rampage'), (5, 'is on a killing spree')]

LOW_TICKET_LIMIT = -100000


def real_time():
    """Real seconds (the game's wall time may stand still within a frame)."""
    try:
        return _time.time()
    except Exception:
        try:
            return host.timer_getWallTime()
        except Exception:
            return 0.0


def err_text():
    e = sys.exc_info()
    try:
        return '%s: %s' % (e[0].__name__, e[1])
    except Exception:
        return str(e[1])


def to_float(v, d):
    try:
        return float(v)
    except Exception:
        return d


def to_int(v, d):
    try:
        return int(float(v))
    except Exception:
        return d


def clean(s):
    s = str(s)
    out = []
    for c in s:
        o = ord(c)
        if c == '"':
            out.append("'")
        elif o < 32 or o > 126:
            out.append('?')
        else:
            out.append(c)
    return ''.join(out)


def dist2(a, b):
    dx = a[0] - b[0]
    dz = a[2] - b[2]
    return dx * dx + dz * dz


def dist3(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def sin_deg(a):
    """sin of an angle in degrees, without the math module."""
    a = float(a) % 360.0
    if a > 180.0:
        a = a - 360.0
    x = a * 0.017453292519943295
    x2 = x * x
    term = x
    total = x
    for i in range(1, 8):
        term = -term * x2 / ((2.0 * i) * (2.0 * i + 1.0))
        total = total + term
    return total


def cos_deg(a):
    return sin_deg(float(a) + 90.0)


def fmt_pos(q):
    if q is None:
        return '?'
    try:
        return '(%.1f, %.2f, %.1f)' % (q[0], q[1], q[2])
    except Exception:
        return str(q)


def ordinal(n):
    if n % 100 in (11, 12, 13):
        return '%dth' % n
    if n % 10 == 1:
        return '%dst' % n
    if n % 10 == 2:
        return '%dnd' % n
    if n % 10 == 3:
        return '%drd' % n
    return '%dth' % n


def parse_arenas(text):
    """'map: x1 z1 x2 z2 [name] | ...' -> {map: (x1, z1, x2, z2, name)}"""
    res = {}
    for part in str(text).split('|'):
        if ':' not in part:
            continue
        i = part.find(':')
        m = part[:i].strip().lower()
        w = part[i + 1:].split()
        if len(w) < 4:
            continue
        try:
            x1 = float(w[0])
            z1 = float(w[1])
            x2 = float(w[2])
            z2 = float(w[3])
        except Exception:
            continue
        name = ' '.join(w[4:])
        if not name:
            name = 'the arena'
        res[m] = (min(x1, x2), min(z1, z2), max(x1, x2), max(z1, z2), name)
    return res


def parse_points(text):
    """'map: x h z yaw [side], ... | ...' -> {map: [(name, x, h, z, yaw, side word)]} (h = the ground)"""
    res = {}
    for part in str(text).split('|'):
        if ':' not in part:
            continue
        i = part.find(':')
        m = part[:i].strip().lower()
        pts = []
        n = 0
        for one in part[i + 1:].split(','):
            w = one.split()
            if len(w) < 3:
                continue
            try:
                x = float(w[0])
                h = float(w[1])
                z = float(w[2])
                yaw = 0.0
                if len(w) > 3:
                    yaw = float(w[3])
            except Exception:
                continue
            side = '0'
            if len(w) > 4:
                side = w[4].lower()
            n = n + 1
            pts.append(('extra_%d' % n, x, h, z, yaw, side))
        if pts:
            if m in res:
                res[m] = res[m] + pts
            else:
                res[m] = pts
    return res


def parse_flag_sides(text):
    """'map: x z side [name], ... | ...' -> {map: [(x, z, side, name)]}"""
    res = {}
    for part in str(text).split('|'):
        if ':' not in part:
            continue
        i = part.find(':')
        m = part[:i].strip().lower()
        rows = []
        for one in part[i + 1:].split(','):
            w = one.split()
            if len(w) < 3:
                continue
            try:
                x = float(w[0])
                z = float(w[1])
                side = int(float(w[2]))
            except Exception:
                continue
            if side not in (0, 1, 2):
                continue
            rows.append((x, z, side, ' '.join(w[3:])))
        if rows:
            res[m] = rows
    return res


def folder_of_script():
    """The server's folder from this file's path (admin/modules/ taken off), or '' when unknown."""
    try:
        f = str(__file__)
    except Exception:
        return ''
    f = f.replace('\\', '/')
    i = f.rfind('/')
    if i < 0:
        return ''
    d = f[:i + 1]
    if not (d.startswith('/') or (len(d) > 1 and d[1] == ':')):
        return ''
    low = d.lower()
    if low.endswith('admin/modules/'):
        d = d[:len(d) - len('admin/modules/')]
    return d


class Rand(object):
    def __init__(self, seed):
        self.s = int(seed * 1000.0) % 2147483647
        if self.s <= 0:
            self.s = 12345

    def below(self, n):
        self.s = (self.s * 48271) % 2147483647
        if n <= 0:
            return 0
        return self.s % n


class FLDeathmatch(object):

    def __init__(self, modManager):
        self.mm = modManager
        self.__state = 0
        self.timer = None
        self.cfg = {}
        self.log_path = None
        self.log_bad = 0
        self.rand = Rand(1.0)
        self.saved_sv = {}      # setting -> the server's own value before we changed it
        self.changed_sv = {}    # setting -> what we set
        self.next_mode = None
        self.limit_override = None
        self.spawners = {}      # bag template -> our ObjectSpawner template (made once a server run)
        self.mags_old = {}      # gun template -> its own nrOfMags (None: not a gun / could not read)
        self.mags_q = []
        self.crate_changed = 0
        self.crate_old = ('7', '3')
        self.cp_tpl_old = {}    # flag template -> its own unableToChangeTeam (None: left alone)
        self.hs_target = 0      # headshots only: wanted / set / cells still to set
        self.hs_on = 0
        self.hs_q = []
        self.hs_heads = 0
        self.hs_set = 0
        self.hs_shown = 0
        self.hs_checked = 0
        self.hs_checked_names = {}
        self.weap_target = {}   # GRENADES / KNIVES / ROCKETS: wanted (1 = they hurt) / announced
        self.weap_on = {}
        for g in WEAPON_GROUPS:
            self.weap_target[g[0]] = 1
            self.weap_on[g[0]] = 1
        self.cells_now = {}     # damage cells set away from the game's: (attack, defence) -> value
        self.dmg_over = {}      # the cells the current plan changes
        self.dmg_label = ''
        self.weap_probed = 0
        self.weap_warned = {}
        self.tz = {}            # TZ_GROUPS: key -> wanted (1 = they hurt) / set / projectile (lower case) ->
        for g in TZ_GROUPS:     # (its name, its own damage as read) / warnings
            self.tz[g[0]] = {'target': 1, 'on': 1, 'old': {}, 'warned': 0}
        self.tz_proj = {}       # gun -> (projectile template, how found, the game's answer)
        self.tz_guard = ''      # the template used as the guard (logged once)
        self.ac_checks = []     # (when, crate, its point's spot, label): where a made crate is after a while
        self.crate_sp = ''      # our ObjectSpawner template for the crates (made once a server run)
        self.ac_found_logged = 0
        self.snipe_said = {}    # player index -> when told that sniper rifles are off
        self.ac_tpl = 0         # arena crates: the crate template changed / its own (refillAmmoSpeed, healSpeed)
        self.ac_tpl_old = ('7', '3')
        self.ac_next = None
        self.ac_q = []
        self.ac_prev = {}
        self.ac_objs = None
        self.ac_stat = {'moved': 0, 'made': 0, 'reused': 0, 'lost': 0, 'unseen': 0, 'at': []}
        self.ac_sets = 0
        self.ac_logged = 0
        self.route_timer = None
        self.delete_works = 1   # 0 once Object.delete left a crate: crates are parked and used again
        self.summarized = 0
        self.playing = 0        # a round is being played (game status Playing)
        self.rcon_on = 0        # the rcon command fldm is registered
        self.reset_round()
        self.active = 0
        self.round_no = 0

    # ------------------------------------------------------------------ settings
    def c(self, name):
        if name in self.cfg:
            return self.cfg[name]
        return configDefaults.get(name)

    def ci(self, name):
        return to_int(self.c(name), to_int(configDefaults.get(name), 0))

    def cf(self, name):
        return to_float(self.c(name), to_float(configDefaults.get(name), 0.0))

    def cs(self, name):
        v = self.c(name)
        if v is None:
            return ''
        return str(v).strip()

    # ------------------------------------------------------------------ log and chat
    def log(self, text):
        t = self.now() - self.t0
        if not self.active:
            t = 0.0
        line = '%s %7.1f %s' % (self.clock(), t, text)
        buf = getattr(self, 'log_buf', None)
        if buf is None:
            buf = []
            self.log_buf = buf
        buf.append(line)
        # lines are kept and written once a second (opening the file for every line cost milliseconds on
        # the test server); errors and long batches go out at once
        if 'ERROR' in text or len(buf) >= 200 or not getattr(self, 'log_buffered', 0):
            self.flush_log()

    def flush_log(self):
        buf = getattr(self, 'log_buf', None)
        if not buf:
            return
        self.log_buf = []
        if self.log_path is None:
            self.log_path = folder_of_script() + self.cs('LOG_FILE')
        r0 = real_time()
        try:
            f = open(self.log_path, 'a')
            f.write('\n'.join(buf) + '\n')
            f.close()
        except Exception:
            self.log_bad = self.log_bad + 1
            if self.log_bad == 1:
                try:
                    self.mm.warn('mm_fldm: cannot write %s (%s)' % (self.log_path, err_text()))
                except Exception:
                    pass
        jm = getattr(self, 'job_ms', None)
        if jm is not None:
            jm['log file'] = jm.get('log file', 0.0) + (real_time() - r0) * 1000.0

    def clock(self):
        try:
            import time
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        except Exception:
            return '-'

    def say(self, text):
        text = clean(text)
        cmax = self.ci('CHAT_MAX')
        if cmax < 40:
            cmax = 40
        parts = []
        while len(text) > cmax:
            cut = text.rfind(' ', 0, cmax)
            if cut < 20:
                cut = cmax
            parts.append(text[:cut])
            text = '  ' + text[cut:].strip()
        parts.append(text)
        for p in parts:
            self.chat_lines = self.chat_lines + 1
            sent = 0
            if mm_utils is not None:
                try:
                    mm_utils.msg_server(p)
                    sent = 1
                except Exception:
                    sent = 0
            if not sent:
                try:
                    host.rcon_invoke('game.sayAll "%s"' % p)
                except Exception:
                    pass
            self.log('chat: ' + p)

    def tsay(self, text):
        if self.ci('TEST_CHAT'):
            self.say(text)
        else:
            self.log('(test chat) ' + clean(text))

    def say_for(self, p, text):
        """Chat for a person; for a bot only the log (and the chat when TEST_CHAT)."""
        if p is not None and self.is_bot(p):
            self.tsay(text)
        else:
            self.say(text)

    def rcon(self, cmd):
        self.calls = self.calls + 1
        try:
            r = host.rcon_invoke(cmd)
            if r is None:
                return ''
            return str(r).strip()
        except Exception:
            return 'ERROR ' + err_text()

    # ------------------------------------------------------------------ small game helpers
    def now(self):
        try:
            return host.timer_getWallTime()
        except Exception:
            return 0.0

    def name_of(self, p):
        try:
            return clean(p.getName()).strip()
        except Exception:
            return '?'

    def players(self):
        self.calls = self.calls + 1
        try:
            return bf2.playerManager.getPlayers()
        except Exception:
            return []

    def by_index(self, i):
        try:
            return bf2.playerManager.getPlayerByIndex(i)
        except Exception:
            return None

    def alive(self, p):
        self.calls = self.calls + 2
        try:
            return p.isAlive() and not p.isManDown()
        except Exception:
            return 0

    def is_bot(self, p):
        try:
            return p.isAIPlayer()
        except Exception:
            return 0

    def team_of(self, p):
        try:
            return p.getTeam()
        except Exception:
            return 0

    def soldier_of(self, p):
        self.calls = self.calls + 1
        try:
            return p.getDefaultVehicle()
        except Exception:
            return None

    def root_of(self, obj):
        o = obj
        n = 0
        while o is not None and n < 8:
            try:
                par = o.getParent()
            except Exception:
                par = None
            if par is None:
                return o
            o = par
            n = n + 1
        return o

    def tpl(self, obj):
        try:
            return str(obj.templateName).lower()
        except Exception:
            return ''

    def is_foot(self, p, root):
        """1 when root is the player's own soldier (or a parachute)."""
        name = self.tpl(root)
        if not name:
            return 1
        if 'parachute' in name:
            return 1
        s = self.soldier_of(p)
        if s is not None and root is s:
            return 1
        if s is not None and self.tpl(s) == name:
            return 1
        if 'soldier' in name:
            return 1
        return 0

    def vehicle_root(self, p):
        """(root, on_foot) for a living player."""
        self.calls = self.calls + 1
        try:
            v = p.getVehicle()
        except Exception:
            v = None
        if v is None:
            return (None, 1)
        r = self.root_of(v)
        return (r, self.is_foot(p, r))

    def pos_of(self, p):
        r = self.vehicle_root(p)[0]
        if r is None:
            r = self.soldier_of(p)
        if r is None:
            return None
        self.calls = self.calls + 1
        try:
            q = r.getPosition()
            return (float(q[0]), float(q[1]), float(q[2]))
        except Exception:
            return None

    def health_of(self, s):
        self.calls = self.calls + 1
        try:
            return float(s.getDamage())
        except Exception:
            return None

    def set_health(self, s, v):
        self.calls = self.calls + 1
        try:
            s.setDamage(v)
            return 1
        except Exception:
            return 0

    def team_name(self, t):
        try:
            n = clean(bf2.gameLogic.getTeamName(t))
            if n:
                return n
        except Exception:
            pass
        return 'team %d' % t

    # ------------------------------------------------------------------ ModManager
    def init(self):
        try:
            self.cfg = self.mm.getModuleConfig(configDefaults)
        except Exception:
            self.cfg = {}
        self.log_path = None
        self.rand = Rand(self.now())
        if 0 == self.__state:
            host.registerHandler('PlayerKilled', self.onPlayerKilled, 1)
            host.registerHandler('PlayerDeath', self.onPlayerDeath, 1)
            host.registerHandler('PlayerSpawn', self.onPlayerSpawn, 1)
            host.registerHandler('EnterVehicle', self.onEnterVehicle, 1)
            host.registerHandler('ExitVehicle', self.onExitVehicle, 1)
            host.registerHandler('PlayerConnect', self.onPlayerConnect, 1)
            host.registerHandler('PlayerDisconnect', self.onPlayerDisconnect, 1)
            host.registerHandler('ChatMessage', self.onChatMessage, 1)
            try:
                host.registerHandler('PlayerChangeWeapon', self.onPlayerChangeWeapon, 1)
            except Exception:
                pass
            try:
                host.registerHandler('PlayerScore', self.onPlayerScore, 1)
            except Exception:
                pass
        host.registerGameStatusHandler(self.onGameStatusChanged)
        if not self.rcon_on:
            try:
                self.mm.registerRconCmdHandler('fldm', {'method': self.cmd_rcon, 'args': 'on | off | status',
                                                        'level': 10})
                self.rcon_on = 1
            except Exception:
                self.log('the rcon command fldm could not be registered (%s)' % err_text())
        self.timer = bf2.Timer(self.onTimer, 0.1, 1)
        self.log_buffered = 1
        self.timer.setRecurring(0.1)
        st = self.cf('TP_STEP')
        if 0.0 < st < 0.1:
            try:
                self.route_timer = bf2.Timer(self.onRouteTimer, max(0.02, st), 1)
                self.route_timer.setRecurring(max(0.02, st))
            except Exception:
                self.route_timer = None
                self.log('the route timer could not be made (%s) - route steps every 0.1 s' % err_text())
        self.__state = 1
        self.log('fldm %s loaded: MODE %s, TEAM_FRAG_LIMIT %d, DROP_MODE %s, arenas: %s'
                 % (VERSION, self.cs('MODE'), self.ci('TEAM_FRAG_LIMIT'),
                    self.cs('DROP_MODE'), ', '.join(list(parse_arenas(self.cs('ARENAS')).keys()))))
        self.log('the log file: %s' % self.log_path)
        st = None
        try:
            st = self.mm.currentGameStatus
        except Exception:
            st = None
        if st == bf2.GameStatus.Playing:
            self.playing = 1
            self.log('loaded during a round: starting it now')
            self.round_start()

    def shutdown(self):
        try:
            if self.dmg_touched():
                self.dmg_reset('shutdown')
            self.tz_reset('shutdown')
            while self.hs_q:
                self.run_hs(0.0, 1000)
        except Exception:
            pass
        try:
            self.flush_log()
        except Exception:
            pass
        self.log_buffered = 0
        if self.timer is not None:
            try:
                self.timer.destroy()
            except Exception:
                pass
            self.timer = None
        if self.route_timer is not None:
            try:
                self.route_timer.destroy()
            except Exception:
                pass
            self.route_timer = None
        try:
            host.unregisterGameStatusHandler(self.onGameStatusChanged)
        except Exception:
            pass
        if self.rcon_on:
            try:
                self.mm.unregisterRconCmdHandler('fldm')
            except Exception:
                pass
            self.rcon_on = 0
        self.restore_settings('shutdown')
        self.active = 0
        self.__state = 2
        self.log('fldm %s shut down' % VERSION)

    def update(self):
        pass

    # ------------------------------------------------------------------ round
    def reset_round(self):
        self.t0 = self.now()
        self.calls = 0
        self.chat_lines = 0
        self.mode = 'off'
        self.map = ''
        self.arena = None
        self.points = []
        self.frags = {}
        self.kills = {}
        self.names = {}
        self.spree = {}
        self.best_spree = {}
        self.last_frag = {}
        self.team_frags = {1: 0, 2: 0}
        self.first_blood = 0
        self.leader = None
        self.leader_tie = 0
        self.warned_left = {}
        self.ended = 0
        self.end_at = None
        self.end_team = 0
        self.setup_at = None
        self.rules_at = None
        self.next_arena = 0.0
        self.next_sec = 0.0
        self.next_slow = 0.0
        self.pending_tp = {}
        self.tp_check = {}
        self.tp_route = {}
        self.guard = {}
        self.spawn_look = {}
        self.spawn_logged = 0
        self.lives = {}
        self.base_spawns = {}
        self.hs_checked = 0
        self.hs_checked_names = {}
        self.snipe_said = {}
        self.ac_next = None
        self.ac_q = []
        self.ac_prev = {}
        self.ac_sets = 0
        self.ac_logged = 0
        self.ac_checks = []
        self.drop_arena = 0
        self.layout = (0, '')
        self.landed = {}
        self.base_seen = {}
        self.base_cache = {}
        self.base_ver = 0
        self.picks_tick = 0
        self.pace = []
        self.pace_logged = 0
        self.pace_early = 0
        self.next_pace = 0.0
        # a crate parked in the sky by the last round stays tracked (lifted while it falls)
        self.crates = [c for c in getattr(self, 'crates', []) if c.get('state') == 'parked']
        self.refill_q = []
        self.refills_logged = 0
        self.removals_logged = 0
        self.speed_ok = 1
        self.spawned_at = {}
        self.out_since = {}
        self.in_veh = {}
        self.kill_on_exit = {}
        self.pending_kill = {}
        self.script_kill = {}
        self.no_drop = {}
        self.point_used = {}
        self.drops_q = []
        self.drops = []
        self.seen_objs = {}
        self.fix = {}
        self.hp_q = []
        self.tts_q = {}
        self.cps = []
        self.tickets_dirty = 1
        self.counts = {'tp_wait': 0, 'tp_none': 0, 'in_arena_spawn': 0, 'tp': 0, 'tp_bad': 0, 'out_kill': 0, 'out_tp': 0, 'veh_warn': 0, 'veh_hp': 0,
                       'veh_kill': 0, 'made': 0, 'made_bad': 0, 'removed': 0, 'gone': 0, 'score_set': 0,
                       'team_moves': 0, 'flag_resets': 0, 'hp': 0, 'frags': 0, 'tks': 0, 'suicides': 0,
                       'not_counted': 0, 'flag_holds': 0, 'tp_up_blocked': 0, 'tp_across_short': 0,
                       'tp_near': 0, 'tp_hurt': 0, 'guard_hp': 0, 'guard_deaths': 0, 'refill': 0,
                       'refill_more': 0, 'refill_unseen': 0, 'refill_reused': 0, 'refill_deleted': 0,
                       'refill_parked': 0, 'refill_lifted': 0, 'spawns': 0, 'spawn_enemy_20m': 0,
                       'spawn_enemy_10m': 0, 'spawn_outside': 0}
        self.score_checked = 0
        self.tts_checked = 0
        self.tts_logged = 0
        self.made_first = {}
        self.drop_checks = []
        self.drops_logged = 0
        self.tp_logged = 0
        self.point_ok = {}
        self.point_fail = {}
        self.force_end_at = None
        self.summarized = 0
        self.forced = None
        self.flag_orig = []
        self.saved_tk = {}
        self.last_real = None
        self.last_tick_ms = 0.0
        self.job_ms = {}
        self.stalls = 0
        self.stall_max = 0.0
        self.stall_max_at = 0.0
        self.stalls_logged = 0
        self.tick_n = 0
        self.allp_tick = None
        self.tick_ms = 0.0
        self.tick_max = 0.0
        self.tick_max_what = ''
        self.slow_ticks = 0

    def onGameStatusChanged(self, status):
        if 1 != self.__state:
            return
        try:
            if status == bf2.GameStatus.Playing:
                self.playing = 1
                self.round_start()
            elif status == bf2.GameStatus.EndGame:
                self.playing = 0
                self.round_end('the game ended the round')
            else:
                self.playing = 0
        except Exception:
            self.log('ERROR in game status %s: %s' % (status, err_text()))

    def round_start(self, forced=None, why=''):
        self.reset_round()
        self.forced = forced
        if not forced or self.round_no == 0:
            self.round_no = self.round_no + 1
        self.t0 = self.now()
        try:
            self.map = str(bf2.gameLogic.getMapName()).lower()
        except Exception:
            self.map = ''
        mode = self.cs('MODE').lower()
        if forced:
            mode = forced
        elif self.next_mode is not None:
            mode = self.next_mode
            self.next_mode = None
        if mode == 'ffa':
            self.log('MODE ffa: free-for-all was taken out in 1.2.7 - team deathmatch instead')
            mode = 'tdm'
        if mode not in ('tdm',):
            mode = 'off'
        arenas = parse_arenas(self.cs('ARENAS'))
        self.arena = arenas.get(self.map)
        pts = []
        if self.ci('BUILTIN_POINTS') and self.map in BUILTIN:
            pts = pts + BUILTIN[self.map]
        if self.ci('MARKED_POINTS') and self.map in MARKED:
            pts = pts + MARKED[self.map]
        if self.ci('MAP_POINTS') and self.map in MAP_PICKED:
            pts = pts + MAP_PICKED[self.map]
        extra = parse_points(self.cs('POINTS'))
        if self.map in extra:
            pts = pts + extra[self.map]
        skip = {}
        for w in self.cs('SKIP_POINTS').replace(',', ' ').split():
            skip[w.strip().lower()] = 1
        self.points = []
        left = []
        twice = []
        gone = TAKEN_OUT.get(self.map, [])
        for pt in pts:
            if str(pt[0]).lower() in skip:
                left.append(pt[0])
                continue
            was = None
            for g in gone:
                if abs(g[1] - pt[1]) < 0.5 and abs(g[2] - pt[3]) < 0.5:
                    was = g[0]
                    break
            if was is not None:
                left.append('%s (= %s, taken out in 1.2.6)' % (pt[0], was))
                continue
            dup = None
            for q in self.points:
                if abs(q[1] - pt[1]) < 0.5 and abs(q[3] - pt[3]) < 0.5 and abs(q[2] - pt[2]) < 1.0:
                    dup = q[0]
                    break
            if dup is not None:
                twice.append('%s (= %s)' % (pt[0], dup))
                continue
            side = 0
            if len(pt) > 5:
                side = self.side_of(pt[5])
            self.points.append((pt[0], pt[1], pt[2], pt[3], pt[4], side))
        if left:
            self.log('points left out (SKIP_POINTS, taken out): %s' % ' '.join(left))
        if twice:
            self.log('points given twice, kept once: %s' % ', '.join(twice[:20]))
        if mode != 'off' and self.arena is None and not self.ci('OTHER_MAPS'):
            mode = 'off'
            self.log('round %d on %s: no arena for this map and OTHER_MAPS 0 - idle' % (self.round_no, self.map))
        self.mode = mode
        if mode == 'off':
            self.active = 0
            self.restore_settings('round without deathmatch')
            return
        self.active = 1
        self.setup_at = self.t0 + 1.0
        self.rules_at = self.t0 + self.ci('RULES_DELAY')
        if forced:
            self.rules_at = self.t0 + 3.0
        a = 'no arena'
        if self.arena is not None:
            a = '%s x %.0f..%.0f z %.0f..%.0f, %d points' % (self.arena[4], self.arena[0], self.arena[2],
                                                              self.arena[1], self.arena[3], len(self.points))
        mid = ''
        if forced:
            mid = ' - turned on in the middle of the round (%s), until it ends' % why
        self.log('round %d on %s: %s, limit %d, %s%s' % (self.round_no, self.map, self.mode_name(),
                                                         self.limit(), a, mid))
        self.apply_settings()

    def side_of(self, word):
        """A point's side from 1 / 2 / 0, a team name (us, mec ...) or any."""
        w = str(word).strip().lower()
        if w in ('1', '2'):
            return int(w)
        if w in ('', '0', 'any', 'all', 'both', '-'):
            return 0
        for t in (1, 2):
            if self.team_name(t).lower() == w:
                return t
        return 0

    def side_word(self, side):
        if side in (1, 2):
            return self.team_name(side).lower()
        return 'any'

    def mode_name(self):
        if self.mode == 'tdm':
            return 'team deathmatch'
        return 'off'

    def limit(self):
        if self.limit_override is not None:
            return self.limit_override
        return max(1, self.ci('TEAM_FRAG_LIMIT'))

    def setup(self):
        """Done 1 s after the round start, after the game mode's own start (gpm_cq sets tickets then)."""
        if not self.saved_tk:
            # a round that starts with deathmatch: the game mode has set the start tickets by now
            self.saved_tk = self.read_tickets()
        self.log('tickets before deathmatch (given back if it is turned off): side 1 %s, side 2 %s'
                 % (self.saved_tk[1][0], self.saved_tk[2][0]))
        if self.forced and self.ci('NO_VEHICLES'):
            for p in self.players():
                try:
                    if not self.alive(p):
                        continue
                    root, foot = self.vehicle_root(p)
                    if not foot:
                        self.onEnterVehicle(p, root)
                except Exception:
                    pass
        try:
            self.setup_flags()
        except Exception:
            self.log('ERROR in the flags setup: %s' % err_text())
        weap = self.weap_wanted()
        whys = []
        if self.ci('HEADSHOTS'):
            whys.append('HEADSHOTS 1')
        for g in WEAPON_GROUPS:
            if not weap[g[0]]:
                whys.append('%s 0' % g[1])
        if whys or self.dmg_touched():
            # every deathmatch round sets its cells again, in case the game reset its damage table in between
            self.dmg_set(self.ci('HEADSHOTS') and 1 or 0, weap, 'new round: ' + (', '.join(whys) or 'all on'), 1)
        self.tz_round()
        for nm in self.cs('INF_NAMES').split(','):
            nm = nm.strip()
            if nm and self.want_mags(nm) and nm not in self.mags_old and nm not in self.mags_q:
                self.mags_q.append(nm)
        if self.ci('HOLD_TICKETS'):
            for t in (1, 2):
                try:
                    bf2.gameLogic.setTicketLimit(t, 1, LOW_TICKET_LIMIT)
                    bf2.gameLogic.setTicketChangePerSecond(t, 0)
                except Exception:
                    self.log('tickets: cannot set the limit / bleed (%s)' % err_text())
            try:
                self.log('tickets: limit now %s / %s; the counters never go under 1 until the winner line, then the '
                         'loser\'s goes to 0 and the game ends the round'
                         % (bf2.gameLogic.getTicketLimit(1, 1), bf2.gameLogic.getTicketLimit(2, 1)))
            except Exception:
                pass
        self.tickets_dirty = 1
        self.update_tickets()

    def read_tickets(self):
        res = {}
        for t in (1, 2):
            rec = [None, None, None]
            try:
                rec[0] = bf2.gameLogic.getTickets(t)
            except Exception:
                pass
            try:
                rec[1] = bf2.gameLogic.getTicketLimit(t, 1)
            except Exception:
                pass
            try:
                rec[2] = bf2.gameLogic.getTicketChangePerSecond(t)
            except Exception:
                pass
            res[t] = rec
        return res

    def setup_flags(self):
        self.cps = []
        try:
            cps = bf2.objectManager.getObjectsOfType(CP_TYPE)
        except Exception:
            cps = []
        self.calls = self.calls + 1
        n = {0: 0, 1: 0, 2: 0}
        out = {0: 0, 1: 0, 2: 0}
        rows = []
        self.flag_orig = []
        for cp in cps:
            try:
                t = int(cp.cp_getParam('team'))
            except Exception:
                t = 0
            u = None
            try:
                u = int(cp.cp_getParam('unableToChangeTeam'))
            except Exception:
                u = None
            self.flag_orig.append((cp, t, u))
            q = None
            try:
                q = cp.getPosition()
                q = (float(q[0]), float(q[1]), float(q[2]))
            except Exception:
                q = None
            inside = 0
            if q is not None and self.arena is not None and self.in_arena(q):
                inside = 1
            if t in n:
                n[t] = n[t] + 1
                if not inside:
                    out[t] = out[t] + 1
            rows.append((cp, t, inside, q))
        self.layout = self.detect_layout(len(rows), [self.tpl(r[0]) for r in rows])
        self.log('layout: %d (%s)' % self.layout)
        plan = self.flag_plan(rows, out)
        changed = []
        for k in range(len(rows)):
            (cp, t, inside, q) = rows[k]
            want = plan[k][0]
            name = plan[k][1]
            if want != t:
                try:
                    cp.cp_setParam('team', want)
                    cp.cp_setParam('flag', want)
                    where = 'outside the arena'
                    if inside:
                        where = 'in the arena'
                    changed.append('%s at %s (%s): side %d -> %d' % (name, fmt_pos(q), where, t, want))
                except Exception:
                    self.log('flag %s at %s: cannot change its side (%s)' % (name, fmt_pos(q), err_text()))
                    want = t
            # arena flags (and those FLAG_SIDES names) are watched every tick, the others every second
            fast = inside or plan[k][2]
            self.cps.append([cp, want, 0, name, 0, fast])
            if self.ci('LOCK_FLAGS'):
                try:
                    cp.cp_setParam('unableToChangeTeam', 1)
                except Exception:
                    pass
        locked = '?'
        if self.cps:
            first = self.cps[0]
            for rec in self.cps:
                if rec[5]:
                    first = rec
                    break
            try:
                locked = '%s for %s' % (first[0].cp_getParam('unableToChangeTeam'), first[3])
            except Exception:
                locked = 'cannot read'
        self.log('flags: %d (side 1: %d, side 2: %d, neutral: %d); the flag object reads unableToChangeTeam %s '
                 'after setting it' % (len(self.cps), n[1], n[2], n[0], locked))
        for c in changed:
            self.log('flag ' + c)
        if self.ci('LOCK_FLAGS'):
            self.lock_templates()

    # ------------------------------------------------------------------ headshots only
    def hs_want(self, on, why):
        self.dmg_set(on and 1 or 0, self.weap_target.copy(), why)

    def weap_wanted(self):
        w = {}
        for g in WEAPON_GROUPS:
            w[g[0]] = self.ci(g[1]) and 1 or 0
        return w

    def dmg_touched(self):
        if self.hs_target or self.hs_on or self.hs_q or self.cells_now:
            return 1
        for g in WEAPON_GROUPS:
            if not self.weap_target[g[0]] or not self.weap_on[g[0]]:
                return 1
        return 0

    def dmg_reset(self, why):
        w = {}
        for g in WEAPON_GROUPS:
            w[g[0]] = 1
        self.dmg_set(0, w, why)

    def dmg_overrides(self):
        """The cells the wanted state changes: (attack, defence) -> value."""
        o = {}
        if self.hs_target:
            for (a, d, v) in HS_CELLS:
                if a not in HS_KEEP:
                    o[(a, d)] = 0.0
            head = self.cf('HS_HEAD')
            if head > 0:
                for (a, d, v) in HS_HEADS:
                    o[(a, d)] = v * head
        for g in WEAPON_GROUPS:
            if not self.weap_target[g[0]]:
                for a in g[3]:
                    for d in SOLDIER_MATS:
                        o[(a, d)] = 0.0
        return o

    def dmg_changes(self, hs, weap, old_hs, old_weap):
        parts = []
        if hs != old_hs:
            parts.append('headshots %s' % (hs and 'ON' or 'off'))
        for g in WEAPON_GROUPS:
            if weap[g[0]] != old_weap[g[0]]:
                parts.append('%s %s' % (g[2], (weap[g[0]] and 'on' or 'OFF')))
        return parts

    def dmg_set(self, hs, weap, why, force=0):
        """Headshots only (hs) and the weapon groups (weap: key -> 1 hurts / 0 does not): queue the damage cells
        that differ from what is set now (force: every changed cell again); run_hs sets them, HS_PER_TICK a tick."""
        parts = self.dmg_changes(hs, weap, self.hs_target, self.weap_target)
        if not parts and not force:
            return 0
        if not parts:
            on = {}
            for g in WEAPON_GROUPS:
                on[g[0]] = 1
            parts = self.dmg_changes(hs, weap, 0, on)
            if not parts:
                parts = ['game damage']
            parts[-1] = parts[-1] + ' again'
        self.hs_target = hs
        self.weap_target = weap.copy()
        o = self.dmg_overrides()
        self.dmg_over = o
        q = []
        keys = list(o.keys())
        keys.sort()
        for k in keys:
            if force or self.cells_now.get(k) != o[k]:
                q.append((k[0], k[1], o[k]))
        keys = list(self.cells_now.keys())
        keys.sort()
        for k in keys:
            if k not in o:
                q.append((k[0], k[1], DMG_DEFAULT.get(k, 1.0)))
        self.hs_q = q
        self.hs_set = 0
        self.dmg_label = ', '.join(parts)
        self.log('%s (%s): %d damage cells to set, %d a tick'
                 % (self.dmg_label, why, len(q), max(1, self.ci('HS_PER_TICK'))))
        if o:
            self.hs_soldier_check()
            self.weap_probe()
        if not q:
            self.run_hs(self.now(), 0)
        return 1

    def run_hs(self, t, n=None):
        if n is None:
            n = max(1, self.ci('HS_PER_TICK'))
        while self.hs_q and n > 0:
            (a, d, v) = self.hs_q.pop(0)
            n = n - 1
            r1 = self.rcon('MaterialManager.createCell %d %d' % (a, d))
            r2 = self.rcon('MaterialManager.damageMod %s' % fmt_num(v))
            if (a, d) in self.dmg_over:
                self.cells_now[(a, d)] = v
            elif (a, d) in self.cells_now:
                del self.cells_now[(a, d)]
            self.hs_set = self.hs_set + 1
            if self.hs_shown < 3 or r1.startswith('ERROR') or r2.startswith('ERROR'):
                self.hs_shown = self.hs_shown + 1
                back = self.rcon('MaterialManager.damageMod')
                self.log('headshots: cell %s x %s -> %s: the game answered "%s" / "%s", damageMod reads "%s"'
                         % (MATERIAL_NAMES.get(a, a), MATERIAL_NAMES.get(d, d), fmt_num(v), r1, r2, back))
        if self.hs_q:
            return
        parts = self.dmg_changes(self.hs_target, self.weap_target, self.hs_on, self.weap_on)
        self.log('%s: %d damage cells set' % (', '.join(parts) or self.dmg_label or 'damage', self.hs_set))
        if self.hs_on != self.hs_target:
            self.hs_on = self.hs_target
            if self.hs_on:
                self.say('[DM] Headshots only: a bullet to the head kills - body shots and grenades do not; knives, '
                         'paddles and AT rockets still do.')
            elif self.active:
                self.say('[DM] Headshots only is off - normal damage again.')
        offs = []
        ons = []
        for g in WEAPON_GROUPS:
            if self.weap_on[g[0]] != self.weap_target[g[0]]:
                self.weap_on[g[0]] = self.weap_target[g[0]]
                if self.weap_on[g[0]]:
                    ons.append(g[2])
                else:
                    offs.append(g[2])
        if offs and self.active:
            self.say('[DM] Off now: %s - they do not hurt soldiers.' % self.weap_words(offs))
        if ons and self.active:
            tail = ''
            if self.hs_on and 'grenades' in ons:
                tail = ' (headshots only is still on, so grenades do not kill yet)'
            self.say('[DM] On again: %s%s.' % (self.weap_words(ons), tail))

    def weap_words(self, names):
        out = []
        for nm in names:
            if nm == 'grenades':
                nm = 'grenades and grenade launchers'
            elif nm == 'rockets':
                nm = 'AT rockets'
            out.append(nm)
        return ', '.join(out)

    def weap_status(self):
        bits = []
        cfgs = []
        for g in WEAPON_GROUPS:
            st = (self.weap_on[g[0]] and 'on' or 'off')
            if self.weap_target[g[0]] != self.weap_on[g[0]]:
                st = st + ' -> ' + (self.weap_target[g[0]] and 'on' or 'off')
            bits.append('%s %s' % (g[2], st))
            cfgs.append('%s %d' % (g[1], self.ci(g[1])))
        for g in TZ_GROUPS:
            if g[11]:
                continue
            ts = self.tz[g[0]]
            st = (ts['on'] and 'on' or 'off')
            if not ts['on']:
                st = st + ' (%d set to damage 0)' % len(ts['old'])
            bits.append('%s %s' % (g[6], st))
            cfgs.append('%s %d' % (g[1], self.ci(g[1])))
        line = '%s (%s)' % (', '.join(bits), ', '.join(cfgs))
        if self.hs_q:
            line = line + ', %d cells left to set' % len(self.hs_q)
        return line

    def weap_cmd(self, key, words, who):
        g = None
        for x in WEAPON_GROUPS:
            if x[0] == key:
                g = x
        if not words or words[0].lower() not in ('on', 'off'):
            return 'fldm: ' + self.weap_status()
        on = (words[0].lower() == 'on') and 1 or 0
        self.cfg[g[1]] = on
        self.log('%s %s by %s (%s %d until the server restarts)' % (g[2], (on and 'on' or 'OFF'), who, g[1], on))
        if not self.active:
            return ('fldm: %s %s from when deathmatch is on (%s %d until the server restarts)'
                    % (g[2], (on and 'on' or 'off'), g[1], on))
        w = self.weap_target.copy()
        w[key] = on
        tzr = 0
        if self.tz_group(key) is not None:
            tzr = self.tz_set(key, on, who)
        if not self.dmg_set(self.hs_target, w, who) and not tzr:
            return 'fldm: %s are already %s - %s' % (g[2], (on and 'on' or 'off'), self.weap_status())
        return 'fldm: ' + self.weap_status()

    # ------------------------------------------------------------------ guns made harmless by their projectile
    # (sniper rifles, stationary MGs, vehicle MGs: their bullets share damage materials with other guns, so their
    # projectiles get ObjectTemplate.damage 0 instead of a damage cell)
    def tz_group(self, key):
        for g in TZ_GROUPS:
            if g[0] == key:
                return g
        return None

    def tz_names(self, key):
        out = []
        for nm in self.cs(self.tz_group(key)[2]).split(','):
            nm = nm.strip().lower()
            if nm and nm not in out:
                out.append(nm)
        return out

    def tz_is(self, key, wname):
        low = str(wname or '').lower()
        if not low:
            return 0
        if low in self.tz_names(key):
            return 1
        for bit in self.tz_group(key)[4]:
            if bit in low:
                return 1
        return 0

    def is_sniper(self, wname):
        return self.tz_is('snipers', wname)

    def tz_touched(self):
        for g in TZ_GROUPS:
            st = self.tz[g[0]]
            if st['old'] or not st['on'] or not st['target'] or not self.ci(g[1]):
                return 1
        return 0

    def tz_reset(self, why):
        for g in TZ_GROUPS:
            st = self.tz[g[0]]
            if st['old'] or not st['on']:
                self.tz_set(g[0], 1, why)

    def tz_round(self):
        """At a deathmatch round's setup: each group as its setting says (off: every projectile set again)."""
        for g in TZ_GROUPS:
            st = self.tz[g[0]]
            if not self.ci(g[1]):
                self.tz_set(g[0], 0, 'new round: %s 0' % g[1], 1)
            elif st['old'] or not st['on']:
                self.tz_set(g[0], 1, 'new round: %s 1' % g[1])

    def tz_guard_on(self, g=None):
        """Make a template we know is no gun active - the crate template (CRATE), else a flag's - and check that
        what is active now is not one of the group's (a bullet; a grenade): a later activeSafe of a name the server
        does not have then leaves that one active, not some real gun. (1.3.3-1.3.8 made a template of their own,
        fldm_guard; templates made while the game runs may upset what the players' games are sent, so not any
        more.)"""
        tried = [('SupplyObject', self.cs('CRATE'))]
        try:
            for cp in bf2.objectManager.getObjectsOfType(CP_TYPE)[:1]:
                tried.append(('ControlPoint', cp.templateName))
        except Exception:
            pass
        for (kind, name) in tried:
            if not name:
                continue
            self.rcon('ObjectTemplate.activeSafe %s %s' % (kind, name))
            if g is None or g[9] == 'material':
                ok = self.rcon('ObjectTemplate.material') not in ('38', '39', '40', '41')
            else:
                ok = self.rcon('ObjectTemplate.%s' % g[9]) not in g[5]
            if ok:
                if self.tz_guard != name:
                    self.tz_guard = name
                    self.log('guns: the guard template is %s %s' % (kind, name))
                return 1
        return 0

    def tz_proj_of(self, w):
        """(projectile template, how it was found, the game's answer to activeSafe) of a gun, once. A name read
        from the gun must start with the gun's own name, else the usual <gun>_Projectile is tried."""
        if w in self.tz_proj:
            return self.tz_proj[w]
        self.tz_guard_on()
        r = self.rcon('ObjectTemplate.activeSafe GenericFireArm %s' % w)
        pt = self.rcon('ObjectTemplate.projectileTemplate').strip().strip('"')
        how = 'read from the gun'
        if key_ok(pt) and pt.lower().startswith(w.lower()):
            pass
        else:
            how = 'guessed (the gun reads "%s")' % pt
            pt = w + '_Projectile'
        self.tz_proj[w] = (pt, how, r)
        return self.tz_proj[w]

    def tz_zero(self, key, w):
        """The group's properties to 0 for one gun's projectile: only a template that reads as one of the group's
        (a bullet of its materials; a grenade's blast 69) with the needed values over 0, made active right after our
        own guard template, is changed - a name the server does not have changes nothing."""
        g = self.tz_group(key)
        st = self.tz[key]
        (pt, how, r) = self.tz_proj_of(w)
        pkey = pt.lower()
        if not self.tz_guard_on(g):
            self.log('%s: %s left alone - a %s template stays active after the guard (%s)'
                     % (g[6], w, (g[9] == 'material' and 'bullet') or 'grenade', self.tz_guard or 'none found'))
            return 0
        self.rcon('ObjectTemplate.activeSafe GenericProjectile %s' % pt)
        ident = self.rcon('ObjectTemplate.%s' % g[9])
        olds = {}
        for (prop, need) in g[10]:
            olds[prop] = self.rcon('ObjectTemplate.%s' % prop)
        if pkey in st['old']:
            if ident in g[5]:
                for (prop, need) in g[10]:
                    if st['old'][pkey][1].get(prop) is not None:
                        self.rcon('ObjectTemplate.%s 0' % prop)
                return 1
            return 0
        ok = ident in g[5]
        for (prop, need) in g[10]:
            v = to_float(olds[prop], -1.0)
            if need and v <= 0:
                ok = 0
            elif not need and v < 0:
                olds[prop] = None
        if not ok:
            said = ['%s "%s"' % (PROP_WORDS.get(g[9], g[9]), ident)]
            for (prop, need) in g[10]:
                said.append('%s "%s"' % (PROP_WORDS.get(prop, prop), olds[prop]))
            self.log('%s: %s left alone - projectile %s (%s; the gun: "%s") reads %s' % (g[6], w, pt, how, r, ', '.join(said)))
            return 0
        done = []
        for (prop, need) in g[10]:
            if olds[prop] is not None:
                self.rcon('ObjectTemplate.%s 0' % prop)
                done.append('%s %s -> 0' % (PROP_WORDS.get(prop, prop), olds[prop]))
        back = self.rcon('ObjectTemplate.%s' % g[10][0][0])
        st['old'][pkey] = (pt, olds)
        self.log('%s: %s - projectile %s (%s): %s (reads "%s")' % (g[6], w, pt, how, ', '.join(done), back))
        return 1

    def tz_set(self, key, on, why, force=0):
        g = self.tz_group(key)
        st = self.tz[key]
        on = on and 1 or 0
        if on == st['target'] and on == st['on'] and not force:
            return 0
        st['target'] = on
        n = 0
        if not on:
            for w in self.tz_names(key):
                n = n + self.tz_zero(key, w)
            self.log('%s OFF (%s): %d %s at damage 0' % (g[6], why, n, g[7]))
        else:
            keys = list(st['old'].keys())
            keys.sort()
            for k in keys:
                (pt, olds) = st['old'][k]
                self.rcon('ObjectTemplate.activeSafe GenericProjectile %s' % pt)
                for (prop, need) in g[10]:
                    if olds.get(prop) is not None:
                        self.rcon('ObjectTemplate.%s %s' % (prop, olds[prop]))
                n = n + 1
            st['old'] = {}
            self.log('%s on (%s): %d projectiles back to their own damage' % (g[6], why, n))
        changed = (st['on'] != on)
        st['on'] = on
        if changed and self.active and not g[11]:
            cap = g[3][0].upper() + g[3][1:]
            if on:
                tail = ''
                if key != 'snipers' and self.ci('NO_VEHICLES'):
                    tail = ' - you may use them, their frags count'
                self.say('[DM] %s are on again%s.' % (cap, tail))
            else:
                self.say('[DM] %s are off: they do no damage and their kills do not count.' % cap)
        return 1

    def tz_cmd(self, key, words, who):
        g = self.tz_group(key)
        if not words or words[0].lower() not in ('on', 'off'):
            return 'fldm: ' + self.weap_status()
        on = (words[0].lower() == 'on') and 1 or 0
        self.cfg[g[1]] = on
        self.log('%s %s by %s (%s %d until the server restarts)' % (g[6], (on and 'on' or 'OFF'), who, g[1], on))
        if not self.active:
            return 'fldm: %s %s from when deathmatch is on (%s %d until the server restarts)' % (
                g[6], (on and 'on' or 'off'), g[1], on)
        if not self.tz_set(key, on, who):
            return 'fldm: %s are already %s - %s' % (g[6], (on and 'on' or 'off'), self.weap_status())
        return 'fldm: ' + self.weap_status()

    def tz_kill(self, wname, aname, vname):
        """A kill by a gun of a group that is off: (key, why) or None; logged as a WARNING (5 times a group)."""
        for g in TZ_GROUPS:
            st = self.tz[g[0]]
            if st['on'] or not self.tz_is(g[0], wname):
                continue
            st['warned'] = st['warned'] + 1
            if st['warned'] <= 5:
                self.log('WARNING: %s killed %s with %s while %s are off - not counted; damage 0 did not stop it '
                         '(%d so far)' % (aname, vname, wname, g[6], st['warned']))
            return (g[0], '%s, %s are off' % (g[8], g[6]))
        return None

    def veh_allowed(self, seat, root):
        """'stationary' / 'vehmg' when this seat may be used though NO_VEHICLES: a stationary MG while
        STATIONARY is on, a vehicle's MG seat while VEHICLE_MG is on; else ''."""
        rname = self.tpl(root).lower()
        sname = self.tpl(seat).lower()
        if self.tz['stationary']['on']:
            for bit in STATIONARY_ROOTS:
                if bit in rname:
                    return 'stationary'
        if self.tz['vehmg']['on']:
            for bit in GUNNER_SEATS:
                if bit in sname or bit in rname:
                    return 'vehmg'
        return ''

    def snipe_tell(self, p):
        """A player took out a sniper rifle while they are off: say so (people only; once a minute a player,
        once in 15 s in all)."""
        if p is None or self.is_bot(p):
            return
        t = self.now()
        last = self.snipe_said.get(p.index)
        if last is not None and t - last < 60.0 and t >= last:
            return
        if t - self.snipe_said.get(-1, -1000.0) < 15.0 and t >= self.snipe_said.get(-1, -1000.0):
            return
        self.snipe_said[p.index] = t
        self.snipe_said[-1] = t
        self.say('[DM] %s: sniper rifles do no damage in this deathmatch - pick another kit.' % self.name_of(p))

    def weap_kill_check(self, wname, what):
        """A kill by a weapon of a group that is off: the cells did not stop it (logged 3 times a weapon)."""
        if not wname or self.hs_q:
            return
        low = wname.lower()
        for g in WEAPON_GROUPS:
            if self.weap_on[g[0]]:
                continue
            for bit in g[4]:
                if bit in low:
                    n = self.weap_warned.get(low, 0) + 1
                    self.weap_warned[low] = n
                    if n <= 3:
                        self.log('WARNING: %s with %s while %s are off - the damage cells did not stop it '
                                 '(%d so far)' % (what, wname, g[2], n))
                    return

    def weap_probe(self):
        """Once a server run: the materials of the projectiles of WEAPON_PROBE, read back from the game."""
        if self.weap_probed:
            return
        self.weap_probed = 1
        for w in WEAPON_PROBE:
            r = self.rcon('ObjectTemplate.activeSafe GenericFireArm %s' % w)
            pt = self.rcon('ObjectTemplate.projectileTemplate').strip()
            if not pt or pt.startswith('ERROR') or ' ' in pt:
                pt = w + '_Projectile'
            self.rcon('ObjectTemplate.activeSafe GenericProjectile %s' % pt)
            m = self.rcon('ObjectTemplate.material')
            em = self.rcon('ObjectTemplate.detonation.explosionMaterial')
            self.log('weapons: %s ("%s"): projectile %s, material "%s", explosion material "%s"' % (w, r, pt, m, em))

    def hs_status(self):
        st = 'off'
        if self.hs_on:
            st = 'on'
        if self.hs_q:
            st = '%s, %d cells left to set (-> %s)' % (st, len(self.hs_q), (self.hs_target and 'on' or 'off'))
        return 'headshots only: %s (HEADSHOTS %d, HS_HEAD %s)' % (st, self.ci('HEADSHOTS'), self.cs('HS_HEAD'))

    def hs_soldier_check(self):
        """Once a round: which materials the soldier templates take explosions on (the cells assume 23/24)."""
        if self.hs_checked:
            return
        for p in self.players():
            try:
                if not self.alive(p):
                    continue
                name = self.tpl(p.getDefaultVehicle())
            except Exception:
                continue
            if not name or name in self.hs_checked_names:
                continue
            self.hs_checked_names[name] = 1
            self.rcon('ObjectTemplate.activeSafe Soldier %s' % name)
            dm = self.rcon('ObjectTemplate.armor.defaultMaterial')
            em = self.rcon('ObjectTemplate.armor.explosionMaterial')
            self.log('headshots: soldier template %s: armor.defaultMaterial "%s", armor.explosionMaterial "%s"'
                     % (name, dm, em))
            if len(self.hs_checked_names) >= 2:
                self.hs_checked = 1
                return

    def detect_layout(self, nflags, names=None):
        """(size, how): LAYOUT, else the size in the flags' template names (cpname_sk_sp16_hotel), else the
        server's map list (the line of maplist.currentMap) when the number of flags fits it, else by the
        number of flags (Karkand: 16 has 4, 64 has 9). The map list alone is not enough: the test server's
        says "gpm_coop 64" while the game loads co-op 16 (25.11.2026)."""
        v = self.cs('LAYOUT').strip().lower()
        if v in ('16', '32', '64'):
            return (int(v), 'LAYOUT %s' % v)
        sizes = {}
        for nm in names or []:
            for tok in str(nm).lower().replace('-', '_').split('_'):
                if tok.startswith('sp'):
                    tok = tok[2:]
                if tok in ('16', '32', '64'):
                    sizes[int(tok)] = sizes.get(int(tok), 0) + 1
        if sizes:
            best = None
            for k in sizes.keys():
                if best is None or sizes[k] > sizes[best]:
                    best = k
            return (best, 'the flag names: %d of %d say %d' % (sizes[best], nflags, best))
        if nflags <= 4:
            by_count = 16
        elif nflags <= 7:
            by_count = 32
        else:
            by_count = 64
        try:
            cur = str(host.rcon_invoke('maplist.currentMap')).strip()
            idx = int(cur.split()[0])
            lst = str(host.rcon_invoke('maplist.list'))
            for line in lst.splitlines():
                line = line.strip()
                if not line.startswith('%d:' % idx):
                    continue
                w = line.replace('"', ' ').split()
                for tok in (w[-1], w[-2]):
                    try:
                        size = int(tok)
                    except Exception:
                        continue
                    if size in (16, 32, 64):
                        if size == by_count or nflags == 0:
                            return (size, 'the map list: %s' % line)
                        return (by_count, '%d flags (the map list says %d: %s)' % (nflags, size, line))
        except Exception:
            pass
        return (by_count, '%d flags' % nflags)

    def layout_plan(self, rows, res):
        """LAYOUT_FLAGS for this map and layout: True when used (res filled)."""
        spec = parse_layout_flags(self.cs('LAYOUT_FLAGS')).get(self.map, {}).get(self.layout[0])
        if not spec:
            return 0
        known = KNOWN_FLAGS.get(self.map, [])
        other = 'keep'
        for (nm, sw) in spec:
            if nm == 'other':
                other = sw
        said = []
        for k in range(len(rows)):
            (cp, t, inside, q) = rows[k]
            key = res[k][1].replace('_', '').replace(' ', '')
            word = None
            hit_name = ''
            for (nm, sw) in spec:
                if nm == 'other':
                    continue
                hit = nm in key
                if not hit and q is not None:
                    for (kn, x, z) in known:
                        if kn == nm and (q[0] - x) * (q[0] - x) + (q[2] - z) * (q[2] - z) < 900.0:
                            hit = 1
                            break
                if hit:
                    word = sw
                    hit_name = nm
                    break
            if word is None:
                word = other
            want = {'us': 2, 'mec': 1, 'neutral': 0}.get(word, t)
            if word not in ('us', 'mec', 'neutral', 'keep'):
                want = self.side_of(word)
                if want not in (0, 1, 2):
                    want = t
            res[k][0] = want
            if hit_name:
                res[k][2] = 1
                said.append('%s %s' % (hit_name, word))
            if inside and want in (1, 2):
                self.drop_arena = 1
        self.log('flags by LAYOUT_FLAGS (layout %d): %s, other %s%s'
                 % (self.layout[0], ', '.join(said) or 'none named found', other,
                    self.drop_arena and '; spawns at the arena flags are dropped too' or ''))
        return 1

    def flag_plan(self, rows, out):
        """[side wanted, name] for every flag row."""
        res = []
        for (cp, t, inside, q) in rows:
            nm = self.tpl(cp) or 'flag'
            res.append([t, nm, 0])
        if self.tdm_base():
            if self.layout_plan(rows, res):
                return res
            if self.ci('NEUTRAL_ARENA'):
                for k in range(len(rows)):
                    (cp, t, inside, q) = rows[k]
                    if inside and t in (1, 2):
                        if out[t] > 0:
                            res[k][0] = 0
                        else:
                            self.log('flags: side %d keeps %s (it has none outside)' % (t, res[k][1]))
            return res
        taken = {}
        for (x, z, side, label) in parse_flag_sides(self.cs('FLAG_SIDES')).get(self.map, []):
            best = None
            bd = 40.0 * 40.0
            for k in range(len(rows)):
                q = rows[k][3]
                if q is None or k in taken:
                    continue
                d = (q[0] - x) * (q[0] - x) + (q[2] - z) * (q[2] - z)
                if d < bd:
                    bd = d
                    best = k
            if best is None:
                self.log('FLAG_SIDES: no flag within 40 m of %.1f %.1f - nothing changed there' % (x, z))
                continue
            taken[best] = 1
            res[best][0] = side
            res[best][2] = 1
            if label:
                res[best][1] = label
        have = {}
        for k in range(len(rows)):
            if (rows[k][2] or k in taken) and res[k][0] in (1, 2):
                have[res[k][0]] = 1
        if self.cs('OUTSIDE_FLAGS').lower() == 'neutral':
            told = {}
            for k in range(len(rows)):
                (cp, t, inside, q) = rows[k]
                if inside or k in taken or t not in (1, 2):
                    continue
                if have.get(t):
                    res[k][0] = 0
                elif not told.get(t):
                    told[t] = 1
                    self.log('flags: side %d has no flag in the arena - it keeps its flags outside' % t)
        return res

    def lock_templates(self):
        """unableToChangeTeam 1 on every flag template (the game mode reads it before any capture)."""
        for rec in self.cps:
            try:
                name = str(rec[0].templateName)
            except Exception:
                continue
            if not name or name in self.cp_tpl_old:
                continue
            self.rcon('ObjectTemplate.activeSafe ControlPoint %s' % name)
            old = self.rcon('ObjectTemplate.unableToChangeTeam')
            w = old.split()
            if not w or w[0] not in ('0', '1'):
                self.cp_tpl_old[name] = None
                self.log('flag template %s: unableToChangeTeam reads "%s" - left alone' % (name, old))
                continue
            self.cp_tpl_old[name] = w[0]
            ans = ''
            if w[0] != '1':
                ans = self.rcon('ObjectTemplate.unableToChangeTeam 1')
            back = self.rcon('ObjectTemplate.unableToChangeTeam')
            obj = '?'
            try:
                obj = str(rec[0].cp_getParam('unableToChangeTeam'))
            except Exception:
                obj = 'cannot read'
            self.log('flag template %s: unableToChangeTeam %s -> 1 ("%s"), the template reads %s, the flag reads %s'
                     % (name, w[0], ans, back, obj))

    def unlock_templates(self):
        done = 0
        for name in list(self.cp_tpl_old.keys()):
            old = self.cp_tpl_old[name]
            if old is None or old == '1':
                continue
            self.rcon('ObjectTemplate.activeSafe ControlPoint %s' % name)
            self.rcon('ObjectTemplate.unableToChangeTeam %s' % old)
            done = done + 1
        if done:
            self.log('flag templates: %d set back to unableToChangeTeam 0' % done)
        self.cp_tpl_old = {}

    def run_flags(self, t, slow=0):
        """A flag keeps its side; one being lowered is raised again; a neutral one does not move. Arena flags
        every tick, the others every second (slow)."""
        if not self.ci('LOCK_FLAGS') or not self.cps or self.setup_at is not None:
            return
        up = self.cf('FLAG_RAISE')
        for rec in self.cps:
            if not slow and not rec[5]:
                continue
            cp = rec[0]
            want = rec[1]
            self.calls = self.calls + 1
            try:
                now_t = int(cp.cp_getParam('team'))
            except Exception:
                continue
            if now_t != want:
                try:
                    cp.cp_setParam('team', want)
                    cp.cp_setParam('flag', want)
                    self.counts['flag_resets'] = self.counts['flag_resets'] + 1
                    if rec[2] < 3:
                        self.log('flag %s changed to side %d - set back to %d' % (rec[3], now_t, want))
                    rec[2] = rec[2] + 1
                except Exception:
                    self.log('flag %s: cannot set back (%s)' % (rec[3], err_text()))
            if not self.speed_ok:
                continue
            self.calls = self.calls + 1
            try:
                sp = float(cp.cp_getParam('takeOverChangePerSecond'))
            except Exception:
                self.speed_ok = 0
                self.log('flags: takeOverChangePerSecond cannot be read (%s) - only the side is put back'
                         % err_text())
                continue
            fix = None
            if want in (1, 2) and sp < 0:
                fix = up
            elif want == 0 and sp != 0:
                fix = 0.0
            if fix is None:
                continue
            try:
                cp.cp_setParam('takeOverChangePerSecond', fix)
                self.counts['flag_holds'] = self.counts['flag_holds'] + 1
                if rec[4] < 3:
                    self.log('flag %s was moving (%.3f a second) - set to %.1f' % (rec[3], sp, fix))
                rec[4] = rec[4] + 1
            except Exception:
                self.speed_ok = 0
                self.log('flags: takeOverChangePerSecond cannot be set (%s)' % err_text())

    def apply_settings(self):
        want = []
        shorter = {}
        if self.ci('RESPAWN') > 0:
            want.append(('sv.spawnTime', str(self.ci('RESPAWN'))))
            shorter['sv.spawnTime'] = 1
        if self.ci('MAN_DOWN') > 0:
            want.append(('sv.manDownTime', str(self.ci('MAN_DOWN'))))
            shorter['sv.manDownTime'] = 1
        names = {}
        for (k, v) in want:
            if k not in self.saved_sv:
                old = self.rcon(k)
                if old and not old.startswith('ERROR') and 'nknown' not in old:
                    self.saved_sv[k] = old.split()[0]
            own = self.saved_sv.get(k)
            if k in shorter and own is not None and to_float(own, 999.0) <= to_float(v, 0.0):
                self.log('setting %s left at the server\'s %s (not longer than %s)' % (k, own, v))
                continue
            names[k] = 1
            self.rcon('%s %s' % (k, v))
            back = self.rcon(k)
            self.changed_sv[k] = v
            self.log('setting %s %s (the server had %s, now reads %s)'
                     % (k, v, self.saved_sv.get(k, '?'), back))
        for k in list(self.changed_sv.keys()):
            if k not in names:
                self.restore_one(k)
        if not self.ci('INF_MAGS'):
            self.mags_back()
        if (self.drop_mode() == 'crate' or self.refill_on()) and self.ci('CRATE_FAST'):
            self.crate_fast(1)
        else:
            self.crate_fast(0)
        if not self.ci('LOCK_FLAGS'):
            self.unlock_templates()

    def crate_fast(self, on):
        """Crate mode: the supply crate template refills and heals at once (it stays so until set back)."""
        name = self.cs('CRATE')
        if on and not self.crate_changed:
            self.rcon('ObjectTemplate.activeSafe SupplyObject %s' % name)
            r = self.rcon('ObjectTemplate.refillAmmoSpeed')
            h = self.rcon('ObjectTemplate.healSpeed')
            old_r = '7'
            old_h = '3'
            if r and to_float(r.split()[0], -1.0) >= 0:
                old_r = r.split()[0]
            if h and to_float(h.split()[0], -1.0) >= 0:
                old_h = h.split()[0]
            self.crate_old = (old_r, old_h)
            a1 = self.rcon('ObjectTemplate.refillAmmoSpeed 1000')
            hv = '100'
            if self.ac_tpl:
                hv = str(max(0, self.ci('ARENA_CRATE_HEAL')))
            a2 = self.rcon('ObjectTemplate.healSpeed %s' % hv)
            self.crate_changed = 1
            self.log('crate %s: refillAmmoSpeed %s -> 1000 ("%s"), healSpeed %s -> %s ("%s"); reads %s / %s'
                     % (name, r, a1, h, hv, a2, self.rcon('ObjectTemplate.refillAmmoSpeed'),
                        self.rcon('ObjectTemplate.healSpeed')))
        elif not on and self.crate_changed:
            self.rcon('ObjectTemplate.activeSafe SupplyObject %s' % name)
            self.rcon('ObjectTemplate.refillAmmoSpeed %s' % self.crate_old[0])
            if self.ac_tpl:
                self.rcon('ObjectTemplate.healSpeed %s' % max(0, self.ci('ARENA_CRATE_HEAL')))
            else:
                self.rcon('ObjectTemplate.healSpeed %s' % self.crate_old[1])
            self.crate_changed = 0
            self.log('crate %s: refillAmmoSpeed back to %s, healSpeed back to %s'
                     % (name, self.crate_old[0], self.crate_old[1]))

    def restore_one(self, k):
        if k in self.saved_sv:
            self.rcon('%s %s' % (k, self.saved_sv[k]))
            self.log('setting %s back to %s' % (k, self.saved_sv[k]))
        try:
            del self.changed_sv[k]
        except Exception:
            pass

    def restore_settings(self, why):
        if self.dmg_touched():
            self.dmg_reset(why)
        self.tz_reset(why)
        self.crate_fast(0)
        self.crate_arena_tpl(0)
        self.mags_back()
        self.unlock_templates()
        if not self.changed_sv:
            return
        self.log('restoring the server settings (%s)' % why)
        for k in list(self.changed_sv.keys()):
            self.restore_one(k)

    def round_end(self, why):
        if not self.active:
            return
        self.log('round %d ended (%s)' % (self.round_no, why))
        try:
            self.clear_crates()
        except Exception:
            self.log('ERROR taking the crates away: %s' % err_text())
        if not self.ended and self.frags:
            self.say(self.standings_line(0))
        if not self.summarized:
            self.summary()
        self.active = 0

    def summary(self):
        self.summarized = 1
        rows = []
        for i in list(self.frags.keys()):
            rows.append((-self.frags[i], self.names.get(i, '?'), i))
        rows.sort()
        self.log('summary: %s, limit %d' % (self.mode_name(), self.limit()))
        if self.mode == 'tdm':
            self.log('  %s %d - %s %d' % (self.team_name(1), self.team_frags[1], self.team_name(2),
                                          self.team_frags[2]))
        for (nf, name, i) in rows:
            d = '?'
            p = self.by_index(i)
            if p is not None:
                try:
                    d = str(p.score.deaths)
                except Exception:
                    d = '?'
            self.log('  %-24s frags %3d  kills %3d  deaths %s  best spree %d'
                     % (name, -nf, self.kills.get(i, 0), d, self.best_spree.get(i, 0)))
        if self.point_ok or self.point_fail:
            self.log('  points (took / did not take): ' + ', '.join(
                ['%s %d/%d' % (self.points[k][0], self.point_ok.get(k, 0), self.point_fail.get(k, 0))
                 for k in range(len(self.points)) if self.point_ok.get(k, 0) or self.point_fail.get(k, 0)]))
        c = self.counts
        if c['spawns']:
            self.log('  spawns by the game: %d, outside the arena %d, an enemy within 20 m %d, within 10 m %d'
                     % (c['spawns'], c['spawn_outside'], c['spawn_enemy_20m'], c['spawn_enemy_10m']))
        if c.get('band_band', 0) or c.get('band_nearer', 0) or c.get('band_farther', 0):
            self.log('  drops: nearest enemy %d-%d m (the band) %d, nearer %d, farther %d; under %d m after waiting %d'
                     % (self.ci('BAND_MIN'), self.ci('BAND_MAX'), c.get('band_band', 0), c.get('band_nearer', 0),
                        c.get('band_farther', 0), self.ci('TP_ENEMY_MIN'), c.get('tp_low', 0)))
        if self.base_spawns and self.ci('BASE_GAP') > 0:
            g2 = float(self.ci('BASE_GAP')) ** 2
            parts = []
            for tm in (1, 2):
                L = self.base_spawns.get(tm, [])
                if not L:
                    continue
                near = [pt[0] for pt in self.points if self.near_base(pt, L, g2)]
                parts.append('%s %d places (points within %d m: %s)' % (self.team_name(tm), len(L),
                                                                       self.ci('BASE_GAP'), ' '.join(near) or '-'))
            self.log('  base spawns learned: ' + '; '.join(parts))
        try:
            self.pace_summary()
        except Exception:
            self.log('  pace: ERROR %s' % err_text())
        if c['refill']:
            self.log('  refill crates: %d (%d of them parked ones used again), taken away by Object.delete %d, '
                     'parked %d, not listed by the server %d' % (c['refill'], c['refill_reused'], c['refill_deleted'],
                                                                c['refill_parked'], c['refill_unseen']))
        keys = list(self.counts.keys())
        keys.sort()
        self.log('  counts: ' + ', '.join(['%s %d' % (k, self.counts[k]) for k in keys]))
        t = self.now() - self.t0
        if t < 1.0:
            t = 1.0
        self.log('  asked of the game this round: ~%d times (%.1f a second), chat lines %d'
                 % (self.calls, self.calls / t, self.chat_lines))
        avg = 0.0
        if self.tick_n:
            avg = self.tick_ms / self.tick_n
        mx = ''
        if self.tick_max_what:
            mx = ' (%s)' % self.tick_max_what
        self.log('  timing: %d server stalls over %s s (longest %.2f s, %.0f s into the round); this script: %d '
                 'ticks, %.1f ms on average, longest %.0f ms%s, %d over 30 ms'
                 % (self.stalls, self.cs('LAG_GAP'), self.stall_max, self.stall_max_at, self.tick_n, avg,
                    self.tick_max, mx, self.slow_ticks))

    # ------------------------------------------------------------------ timer
    def onTimer(self, data=None):
        if 1 != self.__state:
            return
        if not self.active:
            if self.hs_q:
                try:
                    self.run_hs(self.now())
                except Exception:
                    self.log('ERROR in the headshot settings: %s' % err_text())
            if getattr(self, 'log_buf', None):
                self.flush_log()
            return
        r0 = real_time()
        try:
            self.lag_check(r0)
        except Exception:
            pass
        self.job_ms = {}
        try:
            self.tick()
        except Exception:
            self.log('ERROR in the timer: %s' % err_text())
        if getattr(self, 'log_buf', None):
            tn = self.now()
            lf = getattr(self, 'log_flushed', None)
            if lf is None or tn - lf >= 1.0 or tn < lf:
                self.log_flushed = tn
                self.flush_log()
        try:
            self.tick_done((real_time() - r0) * 1000.0)
        except Exception:
            pass

    def lag_check(self, r0):
        """A tick comes every 0.1 s; a longer gap means the server stood still (a stall, felt as lag)."""
        last = self.last_real
        self.last_real = r0
        if last is None:
            return
        gap = r0 - last
        if gap <= self.cf('LAG_GAP') or gap > 600.0:
            return
        self.stalls = self.stalls + 1
        t = self.now() - self.t0
        if gap > self.stall_max:
            self.stall_max = gap
            self.stall_max_at = t
        if self.stalls_logged < self.ci('LAG_LOG'):
            self.stalls_logged = self.stalls_logged + 1
            alive = 0
            try:
                for q in bf2.playerManager.getPlayers():
                    if q.isAlive():
                        alive = alive + 1
            except Exception:
                alive = -1
            self.log('server stall: %.2f s between two ticks (they come every 0.1 s); this script\'s tick before '
                     'it took %.0f ms; %d alive' % (gap, self.last_tick_ms, alive))

    def timed(self, name, fn, *args):
        r0 = real_time()
        fn(*args)
        d = (real_time() - r0) * 1000.0
        if d > 0.0:
            self.job_ms[name] = self.job_ms.get(name, 0.0) + d

    def tick_done(self, ms):
        self.last_tick_ms = ms
        self.tick_n = self.tick_n + 1
        self.tick_ms = self.tick_ms + ms
        what = ''
        if ms >= 30.0:
            jobs = [(-self.job_ms[k], k) for k in list(self.job_ms.keys())]
            jobs.sort()
            what = ', '.join(['%s %.0f ms' % (k, -v) for (v, k) in jobs[:4]])
            self.slow_ticks = self.slow_ticks + 1
            if self.stalls_logged < self.ci('LAG_LOG'):
                self.stalls_logged = self.stalls_logged + 1
                self.log('this script\'s tick took %.0f ms: %s' % (ms, what or '?'))
        if ms > self.tick_max:
            self.tick_max = ms
            self.tick_max_what = what

    def tick(self):
        t = self.now()
        if self.setup_at is not None and t >= self.setup_at:
            self.setup_at = None
            self.timed('round setup', self.setup)
        if self.end_at is not None and t >= self.end_at:
            self.end_at = None
            self.finish_round()
            return
        if self.force_end_at is not None:
            if t >= self.force_end_at:
                self.force_end_at = None
                self.log('the round did not end by the tickets - host.sgl_endGame(%d, 3)' % self.end_team)
                try:
                    host.sgl_endGame(self.end_team, 3)
                except Exception:
                    self.log('host.sgl_endGame failed (%s)' % err_text())
                self.active = 0
            return
        if self.rules_at is not None and t >= self.rules_at:
            self.say_rules()
            ev = self.ci('RULES_EVERY')
            if ev > 0:
                self.rules_at = t + ev
            else:
                self.rules_at = None
        self.timed('mags', self.run_mags)
        self.timed('flags', self.run_flags, t)
        self.timed('moves', self.run_routes, t)
        self.timed('spawn moves', self.run_teleports, t)
        self.timed('protection', self.run_guard, t)
        self.timed('refill', self.run_refill, t)
        self.timed('arena crates', self.run_arena_crates, t)
        self.timed('spawn checks', self.run_spawn_looks, t)
        if self.hs_q:
            self.timed('headshots', self.run_hs, t)
        if self.lives and t >= self.next_pace:
            self.next_pace = t + 0.5
            self.timed('pace', self.run_pace, t)
        self.timed('kills', self.run_kills, t)
        self.timed('vehicles', self.run_vehicles, t)
        self.timed('health', self.run_hp, t)
        self.timed('drops', self.run_drops, t)
        self.timed('drop checks', self.run_drop_checks, t)
        self.timed('scores', self.run_fix)
        self.timed('respawn times', self.run_tts, t)
        if self.tickets_dirty:
            self.timed('tickets', self.update_tickets)
        if self.arena is not None and t >= self.next_arena and self.setup_at is None:
            self.next_arena = t + max(0.2, self.cf('ARENA_EVERY'))
            self.timed('border', self.check_arena, t)
        if t >= self.next_sec:
            self.next_sec = t + 1.0
            self.timed('each second', self.each_second, t)
        if t >= self.next_slow:
            self.next_slow = t + 5.0
            self.timed('each 5 s', self.each_five, t)

    def each_second(self, t):
        if self.ci('HOLD_TICKETS'):
            for tm in (1, 2):
                try:
                    bf2.gameLogic.setTicketChangePerSecond(tm, 0)
                except Exception:
                    pass
            self.calls = self.calls + 2
            self.update_tickets()
        self.run_flags(t, 1)
        # drop items that lived long enough
        if self.drops:
            self.expire_drops(t)
        if self.crates:
            self.lift_parked()

    def each_five(self, t):
        if self.ci('HOLD_TICKETS'):
            for tm in (1, 2):
                try:
                    bf2.gameLogic.setTicketLimit(tm, 1, LOW_TICKET_LIMIT)
                except Exception:
                    pass
        if self.ci('SCORE_IS_FRAGS'):
            for p in self.players():
                self.fix[p.index] = 1

    # ------------------------------------------------------------------ tickets and the end
    def wanted_tickets(self):
        """A side's counter = the frags the other side still needs. Never under 1 before the end."""
        lim = self.limit()
        return {1: max(1, lim - self.team_frags[2]), 2: max(1, lim - self.team_frags[1])}

    def update_tickets(self):
        self.tickets_dirty = 0
        if not self.ci('HOLD_TICKETS') or self.setup_at is not None or self.ended:
            return
        w = self.wanted_tickets()
        for tm in (1, 2):
            self.calls = self.calls + 1
            try:
                if bf2.gameLogic.getTickets(tm) != w[tm]:
                    bf2.gameLogic.setTickets(tm, w[tm])
            except Exception:
                pass

    def start_end(self, team, line):
        if self.ended:
            return
        self.ended = 1
        self.end_team = team
        self.say(line)
        self.say(self.standings_line(1))
        self.end_at = self.now() + max(0, self.ci('END_DELAY'))
        self.log('the limit is reached: %s' % line)

    def finish_round(self):
        team = self.end_team
        loser = 1
        if team == 1:
            loser = 2
        self.log('ending the round: winner side %d - side %d\'s tickets to 0' % (team, loser))
        self.summary()
        try:
            bf2.gameLogic.setTickets(loser, 0)
        except Exception:
            self.log('setting the tickets failed (%s)' % err_text())
        self.force_end_at = self.now() + 2.0

    def standings_line(self, final):
        if self.mode == 'tdm':
            a = '%s %d - %s %d' % (self.team_name(1), self.team_frags[1], self.team_name(2), self.team_frags[2])
            rows = self.top_rows(3)
            best = ''
            if rows:
                best = ' | best: ' + ', '.join(['%s %d' % (r[1], -r[0]) for r in rows])
            if final:
                return '[DM] Final: ' + a + best
            return '[DM] ' + a + ' (to %d)' % self.limit() + best
        rows = self.top_rows(5)
        if not rows:
            return '[DM] No frags yet. First to %d wins.' % self.limit()
        s = '  '.join(['%d. %s %d' % (k + 1, rows[k][1], -rows[k][0]) for k in range(len(rows))])
        if final:
            return '[DM] Final: ' + s
        return '[DM] ' + s + ' (to %d)' % self.limit()

    def top_rows(self, n):
        rows = []
        for i in list(self.frags.keys()):
            rows.append((-self.frags[i], self.names.get(i, '?'), i))
        rows.sort()
        return rows[:n]

    def place_of(self, i):
        mine = self.frags.get(i, 0)
        better = 0
        for k in list(self.frags.keys()):
            if self.frags[k] > mine:
                better = better + 1
        return better + 1

    def say_rules(self):
        lim = self.limit()
        where = ''
        if self.arena is not None and self.border_on():
            where = ' Arena: %s - leave it and you die.' % self.arena[4]
        veh = ''
        if self.ci('NO_VEHICLES'):
            veh = ' No vehicles.'
        holds = []
        for rec in self.cps:
            if rec[1] in (1, 2) and rec[3] and not rec[3].startswith('cp') and rec[3] != 'flag':
                holds.append('%s holds %s' % (self.team_name(rec[1]), rec[3]))
        ht = ''
        if holds:
            ht = ' ' + ', '.join(holds) + '.'
        if self.tdm_base() and self.tp_on():
            ht = ' You spawn at your base and drop into the arena at a random spot.'
            if self.drop_arena:
                ht = ' You spawn at your flags and drop into the arena at a random spot.'
        if self.hs_target:
            ht = ht + ' Headshots only.'
        offs = []
        for g in WEAPON_GROUPS:
            if not self.weap_target[g[0]]:
                offs.append(g[2])
        for g in TZ_GROUPS:
            if not self.tz[g[0]]['target'] and not g[11]:
                offs.append(g[3])
        if offs:
            ht = ht + ' Off: %s.' % self.weap_words(offs)
        self.say('[DM] Team deathmatch: first side to %d frags wins.%s%s%s' % (lim, ht, where, veh))
        extra = []
        dm = self.drop_mode()
        if dm == 'crate':
            extra.append('the dead drop a supply crate')
        elif dm != 'off' and (self.ci('DROP_MED') > 0 or self.ci('DROP_AMMO') > 0):
            extra.append('the dead drop %d medic + %d ammo bags' % (self.ci('DROP_MED'), self.ci('DROP_AMMO')))
        gift = []
        if self.ci('FRAG_HP') >= self.ci('HP_MAX'):
            gift.append('full health')
        elif self.ci('FRAG_HP') > 0:
            gift.append('+%d health' % self.ci('FRAG_HP'))
        if self.refill_on():
            gift.append('an ammo crate')
        if gift:
            extra.append(' and '.join(gift) + ' for every frag')
        if self.cf('SPAWN_GUARD') > 0:
            extra.append('%s s spawn protection' % ('%.1f' % self.cf('SPAWN_GUARD')).replace('.0', ''))
        if self.ci('INF_MAGS'):
            extra.append('endless magazines')
        if self.ac_count() > 0:
            extra.append('%d ammo crates%s move round the arena every %d s'
                         % (self.ac_count(), (self.ci('ARENA_CRATE_HEAL') <= 0 and ' (no healing)') or '',
                            max(10, self.ci('ARENA_CRATE_EVERY'))))
        if self.ci('PUBLIC_SCORE'):
            extra.append('type !dm for the score')
        if extra:
            self.say('[DM] ' + ', '.join(extra) + '.')

    # ------------------------------------------------------------------ events
    def onPlayerConnect(self, p):
        if 1 != self.__state or not self.active:
            return
        try:
            self.names[p.index] = self.name_of(p)
        except Exception:
            self.log('ERROR in connect: %s' % err_text())

    def onPlayerDisconnect(self, p):
        if 1 != self.__state or not self.active:
            return
        try:
            i = p.index
            for d in (self.pending_tp, self.tp_check, self.out_since, self.in_veh, self.kill_on_exit,
                      self.pending_kill, self.tts_q, self.fix, self.tp_route, self.guard,
                      self.spawn_look, self.lives):
                if i in d:
                    del d[i]
        except Exception:
            pass

    def onPlayerSpawn(self, p, soldier):
        if 1 != self.__state or not self.active:
            return
        try:
            i = p.index
            t = self.now()
            self.names[i] = self.name_of(p)
            self.spawned_at[i] = t
            for d in (self.out_since, self.in_veh, self.kill_on_exit, self.pending_kill):
                if i in d:
                    del d[i]
            if i not in self.frags:
                self.frags[i] = 0
                self.kills[i] = 0
            for d in (self.tp_route, self.tp_check):
                if i in d:
                    del d[i]
            if i in self.tts_q:
                del self.tts_q[i]
            moved = self.arena is not None and self.tp_on() and self.points
            if moved:
                self.pending_tp[i] = [t + max(0.0, self.cf('TP_DELAY')), t]
            else:
                self.spawn_look[i] = t + 0.6
            self.life_begin(p, soldier, t, not moved)
            g = self.cf('SPAWN_GUARD')
            if g > 0:
                self.guard[i] = t + g
        except Exception:
            self.log('ERROR in spawn: %s' % err_text())

    def tdm_base(self):
        return self.mode == 'tdm' and self.cs('TDM_SPAWN').lower() != 'flag'

    def tp_on(self):
        v = self.cs('SPAWN_TP').lower()
        if v in ('0', 'off', 'no', 'none', ''):
            return 0
        if v in ('all', '2', 'both'):
            return 1
        return self.tdm_base()

    def onPlayerDeath(self, p, soldier):
        if 1 != self.__state or not self.active:
            return
        try:
            i = p.index
            t = self.now()
            for d in (self.pending_tp, self.out_since, self.in_veh, self.kill_on_exit, self.pending_kill,
                      self.tp_route, self.tp_check, self.guard, self.spawn_look):
                if i in d:
                    del d[i]
            self.life_end(i, t, 'died')
            if i in self.landed:
                del self.landed[i]
            if self.ci('HOLD_TICKETS') and self.setup_at is None and self.force_end_at is None:
                tm = self.team_of(p)
                if tm in (1, 2):
                    try:
                        bf2.gameLogic.setTickets(tm, bf2.gameLogic.getTickets(tm) + 1)
                    except Exception:
                        pass
            if self.ci('RESPAWN') > 0:
                self.tts_q[i] = [t + 0.05, t + max(0, self.ci('MAN_DOWN')) + 8.0]
            self.tickets_dirty = 1
        except Exception:
            self.log('ERROR in death: %s' % err_text())

    def onPlayerScore(self, p, difference=0):
        if 1 != self.__state or not self.active or not self.ci('SCORE_IS_FRAGS'):
            return
        try:
            self.fix[p.index] = 1
        except Exception:
            pass

    def onEnterVehicle(self, p, vehicle, freeSoldier=False):
        if 1 != self.__state or not self.active or not self.ci('NO_VEHICLES'):
            return
        try:
            root = self.root_of(vehicle)
            if self.is_foot(p, root):
                return
            i = p.index
            name = self.tpl(root)
            allowed = self.veh_allowed(vehicle, root)
            if allowed:
                self.log('%s got into %s (seat %s): allowed, %s are on' % (self.name_of(p), name, self.tpl(vehicle),
                                                                          self.tz_group(allowed)[6]))
                return
            self.in_veh[i] = {'since': self.now(), 'name': name, 'root': root, 'done': 0}
            self.counts['veh_warn'] = self.counts['veh_warn'] + 1
            self.say_for(p, '[DM] %s: no vehicles in deathmatch - get out within %d s'
                         % (self.name_of(p), self.ci('VEH_GRACE')))
            seat = self.tpl(vehicle)
            if seat and seat != name:
                self.log('%s got into %s (seat %s)' % (self.name_of(p), name, seat))
            else:
                self.log('%s got into %s' % (self.name_of(p), name))
        except Exception:
            self.log('ERROR in enter vehicle: %s' % err_text())

    def onExitVehicle(self, p, vehicle):
        if 1 != self.__state or not self.active:
            return
        try:
            i = p.index
            if i in self.in_veh:
                del self.in_veh[i]
            if i in self.kill_on_exit:
                del self.kill_on_exit[i]
                self.pending_kill[i] = [self.now() + 0.2, 'stayed in a vehicle', 0]
        except Exception:
            self.log('ERROR in exit vehicle: %s' % err_text())

    def onPlayerChangeWeapon(self, p, oldWeapon=None, newWeapon=None):
        if 1 != self.__state or not self.active:
            return
        try:
            self.mags_for(newWeapon)
        except Exception:
            pass
        try:
            if not self.tz['snipers']['on'] and newWeapon is not None and self.is_sniper(self.tpl(newWeapon)):
                self.snipe_tell(p)
        except Exception:
            self.log('ERROR in the sniper check: %s' % err_text())

    def onPlayerKilled(self, victim, attacker, weapon, assists, victimSoldier):
        if 1 != self.__state or not self.active:
            return
        try:
            self.mags_for(weapon)
        except Exception:
            pass
        try:
            self.killed(victim, attacker, weapon, victimSoldier)
        except Exception:
            self.log('ERROR in kill: %s' % err_text())

    def killed(self, victim, attacker, weapon, vsoldier):
        if victim is None:
            return
        t = self.now()
        vi = victim.index
        vname = self.name_of(victim)
        self.names[vi] = vname
        vteam = self.team_of(victim)
        if vi not in self.frags:
            self.frags[vi] = 0
            self.kills[vi] = 0
        pos = None
        if vsoldier is not None:
            try:
                q = vsoldier.getPosition()
                pos = (float(q[0]), float(q[1]), float(q[2]))
            except Exception:
                pos = None
        wname = ''
        if weapon is not None:
            wname = self.tpl(weapon)
        scripted = 0
        if vi in self.script_kill and t - self.script_kill[vi] < 3.0:
            scripted = 1
            del self.script_kill[vi]
        kind = 'frag'
        ai = None
        aname = ''
        if attacker is None or attacker.index == vi:
            kind = 'suicide'
        else:
            ai = attacker.index
            aname = self.name_of(attacker)
            self.names[ai] = aname
            if ai not in self.frags:
                self.frags[ai] = 0
                self.kills[ai] = 0
            if self.mode == 'tdm' and self.team_of(attacker) == vteam:
                kind = 'tk'
        why = ''
        if kind == 'frag':
            if self.ci('NO_VEHICLES') and self.alive(attacker):
                wroot, afoot = self.vehicle_root(attacker)
                seat = None
                if not afoot:
                    try:
                        seat = attacker.getVehicle()
                    except Exception:
                        seat = None
                if not afoot and not self.veh_allowed(seat, wroot):
                    kind = 'none'
                    why = 'from a vehicle (%s)' % self.tpl(wroot)
            if kind == 'frag' and self.ci('NO_ARTY_FRAGS'):
                if 'ars_' in wname or 'artillery' in wname or 'usart' in wname:
                    kind = 'none'
                    why = 'artillery'
        if kind in ('frag', 'none') and ai is not None:
            hit = self.tz_kill(wname, aname, vname)
            if hit and kind == 'frag':
                kind = 'none'
                why = hit[1]
        if self.ended:
            self.log('after the end: %s killed %s (%s) - not counted' % (aname, vname, wname))
            return
        how = kind
        if kind == 'frag':
            how = 'fragged by %s' % aname
            self.life_mark(ai, 'frag', t)
        elif kind == 'tk':
            how = 'team-killed by %s' % aname
        elif kind == 'none':
            how = 'killed by %s (%s)' % (aname, why)
        elif scripted:
            how = 'killed by the script'
        self.life_end(vi, t, how)
        if vi in self.guard:
            if t <= self.guard[vi] and not scripted:
                self.counts['guard_deaths'] = self.counts['guard_deaths'] + 1
                self.log('%s died %.1f s after his spawn, while protected (%s, %s)'
                         % (vname, t - self.spawned_at.get(vi, t), wname or '?', kind))
            del self.guard[vi]
        # the victim's spree ends
        vs = self.spree.get(vi, 0)
        self.spree[vi] = 0
        ateam = 0
        if ai is not None:
            ateam = self.team_of(attacker)
        if kind == 'suicide':
            self.frags[vi] = self.frags[vi] - 1
            if self.mode == 'tdm' and vteam in self.team_frags:
                self.team_frags[vteam] = self.team_frags[vteam] - 1
            self.counts['suicides'] = self.counts['suicides'] + 1
            how = 'suicide'
            if scripted:
                how = 'killed by the script'
            self.log('%s: %s (%s), frags %d' % (vname, how, wname, self.frags[vi]))
        elif kind == 'tk':
            self.frags[ai] = self.frags[ai] - 1
            if ateam in self.team_frags:
                self.team_frags[ateam] = self.team_frags[ateam] - 1
            self.counts['tks'] = self.counts['tks'] + 1
            self.log('%s team-killed %s (%s): -1, frags %d' % (aname, vname, wname, self.frags[ai]))
            if self.ci('ANNOUNCE'):
                self.say('[DM] %s: -1 for a team kill' % aname)
        elif kind == 'none':
            self.counts['not_counted'] = self.counts['not_counted'] + 1
            self.log('%s killed %s: not counted, %s' % (aname, vname, why))
            self.say('[DM] %s: frag not counted (%s)' % (aname, why.split(' (')[0]))
        else:
            self.frag(ai, attacker, aname, vi, vname, wname, ateam, t)
        if vs >= max(1, self.ci('SPREE')) and self.ci('ANNOUNCE'):
            if kind == 'frag':
                self.say('[DM] %s ended %s\'s killing spree (%d)' % (aname, vname, vs))
            else:
                self.say('[DM] %s\'s killing spree ended (%d)' % (vname, vs))
        if ai is not None:
            self.fix[ai] = 1
        self.fix[vi] = 1
        self.tickets_dirty = 1
        # drops
        if pos is not None and self.drop_mode() != 'off' and not scripted:
            inside = 1
            if self.arena is not None and not self.ci('DROP_OUTSIDE'):
                inside = self.in_arena(pos)
            if inside:
                team = 0
                dt = self.cs('DROP_TEAM')
                if dt == 'killer' and ai is not None:
                    team = ateam
                elif dt == 'victim' or (dt == 'killer' and ai is None):
                    team = vteam
                self.drops_q.append((t, pos, team, vname))
        self.check_limit(ai, aname, ateam)

    def frag(self, ai, attacker, aname, vi, vname, wname, ateam, t):
        self.frags[ai] = self.frags[ai] + 1
        self.kills[ai] = self.kills.get(ai, 0) + 1
        if self.mode == 'tdm' and ateam in self.team_frags:
            self.team_frags[ateam] = self.team_frags[ateam] + 1
        self.counts['frags'] = self.counts['frags'] + 1
        sp = self.spree.get(ai, 0) + 1
        self.spree[ai] = sp
        if sp > self.best_spree.get(ai, 0):
            self.best_spree[ai] = sp
        self.log('%s fragged %s (%s): frags %d, spree %d' % (aname, vname, wname, self.frags[ai], sp))
        self.weap_kill_check(wname, '%s fragged %s' % (aname, vname))
        ann = self.ci('ANNOUNCE')
        if ann:
            if not self.first_blood:
                self.say('[DM] First blood: %s' % aname)
            if 'knife' in wname or 'defib' in wname:
                self.say('[DM] Humiliation! %s %s %s' % (aname, self.verb(wname), vname))
            last = self.last_frag.get(ai)
            if last is not None and t - last <= self.cf('EXCELLENT'):
                self.say('[DM] %s: Excellent!' % aname)
            step = max(1, self.ci('SPREE'))
            if sp % step == 0:
                word = SPREE_WORDS[-1][1]
                for (n, w) in SPREE_WORDS:
                    if sp >= n:
                        word = w
                        break
                self.say('[DM] %s %s (%d)' % (aname, word, sp))
        self.first_blood = 1
        self.last_frag[ai] = t
        hp = self.ci('FRAG_HP')
        if hp > 0:
            self.hp_q.append((t + 0.1, ai, hp, 0))
        if self.ci('GUARD_ENDS_ON_FRAG') and ai in self.guard:
            del self.guard[ai]
        if self.refill_on():
            self.refill_q.append((t + 0.05, ai))

    def verb(self, wname):
        if 'defib' in wname:
            return 'shocked'
        return 'knifed'

    def check_limit(self, ai, aname, ateam):
        lim = self.limit()
        if ateam not in (1, 2):
            return
        f = self.team_frags[ateam]
        if f >= lim:
            self.start_end(ateam, '[DM] %s wins %d - %d!' % (self.team_name(ateam), f,
                                                            self.team_frags[3 - ateam]))
            return
        left = lim - f
        if self.ci('ANNOUNCE') and f >= self.team_frags[3 - ateam]:
            for w in self.cs('LEFT_WARN').split():
                key = left * 10 + ateam
                if to_int(w, -1) == left and not self.warned_left.get(key):
                    self.warned_left[key] = 1
                    word = 'frags'
                    if left == 1:
                        word = 'frag'
                    self.say('[DM] %s needs %d more %s (%d - %d)' % (self.team_name(ateam), left, word, f,
                                                                    self.team_frags[3 - ateam]))

    def is_top(self, i):
        f = self.frags.get(i, 0)
        for k in list(self.frags.keys()):
            if k != i and self.frags[k] > f:
                return 0
        return 1

    # ------------------------------------------------------------------ the arena
    def in_arena(self, pos):
        a = self.arena
        if a is None:
            return 1
        return a[0] <= pos[0] <= a[2] and a[1] <= pos[2] <= a[3]

    def everybody(self):
        """Every living soldier: (index, side, place, facing yaw or None)."""
        res = []
        for q in self.players():
            if not self.alive(q):
                continue
            r, foot = self.vehicle_root(q)
            if r is None:
                r = self.soldier_of(q)
            if r is None:
                continue
            self.calls = self.calls + 2
            try:
                pq = r.getPosition()
                pq = (float(pq[0]), float(pq[1]), float(pq[2]))
            except Exception:
                continue
            yaw = None
            if foot:
                try:
                    yaw = float(r.getRotation()[0])
                except Exception:
                    yaw = None
            res.append((q.index, self.team_of(q), pq, yaw))
        return res

    def everybody_recent(self, t):
        """everybody(), read again at most every 0.5 s: the spawn picks, the pace and the spawn statistics share
        it (on the test server reading every soldier cost ~30-60 ms a spawn; with_targets puts the soldiers
        moved since the read where they landed or will land)."""
        c = getattr(self, 'allp_cache', None)
        if c is None or t - c[0] > 0.5 or t < c[0]:
            c = (t, self.everybody())
            self.allp_cache = c
        return c[1]

    def watchers(self, p, allp=None):
        """Living enemies of p (p None: everybody alive) as (place, facing yaw or None)."""
        if allp is None:
            allp = self.everybody()
        me = -1
        myteam = 0
        if p is not None:
            me = p.index
            myteam = self.team_of(p)
        res = []
        for (i, tm, pq, yaw) in allp:
            if i == me:
                continue
            if p is not None and self.mode == 'tdm' and tm == myteam:
                continue
            res.append((pq, yaw))
        return res

    def sees(self, w, spot, near2, far2, cone_cos):
        (pq, yaw) = w
        dx = spot[0] - pq[0]
        dz = spot[2] - pq[2]
        d2 = dx * dx + dz * dz
        if d2 < near2:
            return 1
        if d2 >= far2:
            return 0
        if yaw is None:
            return 1
        d = d2 ** 0.5
        if d <= 0.0:
            return 1
        c = (sin_deg(yaw) * dx + cos_deg(yaw) * dz) / d
        return c >= cone_cos

    def point_bad(self, k):
        f = self.point_fail.get(k, 0)
        return f >= 2 and f > self.point_ok.get(k, 0)

    def rank_points(self, p, allp=None, skip=-1, low=0):
        """Arena points, best first: (blocked, seen by how many, -distance to the nearest enemy, random, k).
        blocked: 0 free, 1 used in the last SPAWN_RECENT s, 2 somebody standing on it or an enemy within
        TP_ENEMY_MIN (low: TP_ENEMY_LOW), 3 failed twice this round (or the point just missed). tdm: only the
        points of his side (and those of no side)."""
        t = self.now()
        if allp is None:
            allp = self.everybody()
        ws = self.watchers(p, allp)
        me = -1
        myside = 0
        if p is not None:
            me = p.index
            if self.mode == 'tdm':
                myside = self.team_of(p)
        near2 = float(self.ci('SEE_NEAR')) ** 2
        far2 = float(self.ci('SEE_FAR')) ** 2
        cone_cos = cos_deg(self.ci('SEE_CONE'))
        clear2 = self.cf('TP_CLEAR') ** 2
        emin = max(0, self.ci('TP_ENEMY_MIN'))
        if low:
            emin = min(emin, max(0, self.ci('TP_ENEMY_LOW')))
        enemy2 = float(emin) ** 2
        recent = self.cf('SPAWN_RECENT')
        near_base = self.base_blocked(p)
        # the watchers once: place, and the facing as sin / cos (or None: sees all round)
        wl = []
        for (pq, yaw) in ws:
            if yaw is None:
                wl.append((pq[0], pq[2], None, None))
            else:
                wl.append((pq[0], pq[2], sin_deg(yaw), cos_deg(yaw)))
        others = []
        for (i, tm, pq, yaw) in allp:
            if i != me:
                others.append(pq)
        used = self.point_used
        rows = []
        points = self.points
        for k in range(len(points)):
            pt = points[k]
            side = 0
            if len(pt) > 5:
                side = pt[5]
            if myside and side and side != myside:
                continue
            if k in near_base:
                continue
            sx = pt[1]
            sz = pt[3]
            seen = 0
            d = 1e12
            for (wx, wz, ws_, wc) in wl:
                dx = sx - wx
                dz = sz - wz
                dd = dx * dx + dz * dz
                if dd < d:
                    d = dd
                if dd < near2:
                    seen = seen + 1
                elif dd < far2:
                    if ws_ is None:
                        seen = seen + 1
                    elif dd > 0.0 and (ws_ * dx + wc * dz) >= cone_cos * (dd ** 0.5):
                        seen = seen + 1
            blocked = 0
            if k == skip or self.point_bad(k):
                blocked = 3
            else:
                sy = pt[2]
                for pq in others:
                    dx = sx - pq[0]
                    dz = sz - pq[2]
                    if dx * dx + dz * dz < clear2 and abs(pq[1] - sy) < 3.0:
                        blocked = 2
                        break
                if not blocked and d < enemy2:
                    blocked = 2
                if not blocked and k in used and t - used[k] < recent:
                    blocked = 1
            rows.append((blocked, seen, -d, self.rand.below(1000), k))
        rows.sort()
        return rows

    def base_blocked(self, p):
        """Points within BASE_GAP of the enemy's learned base spawn places: {k: 1}, kept until a place is
        added."""
        if self.ci('BASE_GAP') <= 0 or not self.base_spawns or p is None:
            return {}
        tm = self.team_of(p)
        key = (tm, self.base_ver)
        c = self.base_cache.get(tm)
        if c is not None and c[0] == key:
            return c[1]
        bases = self.enemy_bases(p)
        gap2 = float(max(0, self.ci('BASE_GAP'))) ** 2
        res = {}
        for k in range(len(self.points)):
            if self.near_base(self.points[k], bases, gap2):
                res[k] = 1
        self.base_cache[tm] = (key, res)
        return res

    def with_targets(self, allp):
        """Soldiers on the way (sky route) counted where they will land, and those landed in the last second
        where they landed (the soldiers' places may be up to 0.5 s old) - also when the read missed them."""
        t = self.now()
        landed = self.landed
        for i in list(landed.keys()):
            if t - landed[i][0] > 1.0 or t < landed[i][0]:
                del landed[i]
        if not self.tp_route and not landed:
            return allp
        up = self.cf('TP_UP')
        res = []
        done = {}
        for (i, tm, pq, yaw) in allp:
            done[i] = 1
            r = self.tp_route.get(i)
            if r is not None:
                tg = r['target']
                res.append((i, tm, (tg[0], tg[1] - up, tg[2]), None))
            elif i in landed:
                res.append((i, tm, landed[i][2], None))
            else:
                res.append((i, tm, pq, yaw))
        for i in list(self.tp_route.keys()):
            if i not in done:
                r = self.tp_route[i]
                tg = r['target']
                res.append((i, r.get('tm', 0), (tg[0], tg[1] - up, tg[2]), None))
                done[i] = 1
        for i in list(landed.keys()):
            if i not in done:
                res.append((i, landed[i][1], landed[i][2], None))
        return res

    def learn_base(self, p, here):
        """A place where the game spawned somebody at his base (before the move), by side."""
        if self.ci('BASE_GAP') <= 0:
            return
        tm = self.team_of(p)
        L = self.base_spawns.get(tm)
        if L is None:
            L = []
            self.base_spawns[tm] = L
        for q in L:
            if dist2(q, here) < 16.0:
                return
        # a place counts once the game has spawned somebody there twice (a squad spawn that slipped
        # through, or a one-off, does not make the points round it unusable)
        seen = self.base_seen.get(tm)
        if seen is None:
            seen = []
            self.base_seen[tm] = seen
        for k in range(len(seen)):
            if dist2(seen[k], here) < 16.0:
                del seen[k]
                if len(L) < 40:
                    L.append(here)
                    self.base_ver = self.base_ver + 1
                return
        if len(seen) < 200:
            seen.append(here)

    def enemy_bases(self, p):
        """The learned base spawn places of his enemies (the other side's)."""
        if self.ci('BASE_GAP') <= 0 or not self.base_spawns:
            return []
        if self.mode == 'tdm' and p is not None:
            tm = self.team_of(p)
            out = []
            for k in self.base_spawns.keys():
                if k != tm:
                    out = out + self.base_spawns[k]
            return out
        out = []
        for k in self.base_spawns.keys():
            out = out + self.base_spawns[k]
        return out

    def near_base(self, pt, bases, gap2):
        for q in bases:
            if (q[0] - pt[1]) ** 2 + (q[2] - pt[3]) ** 2 < gap2:
                return 1
        return 0

    def pick_point(self, p, allow=0, skip=-1):
        """(k, distance to the nearest enemy, enemies, seen by, how), or None when no point is blocked at most
        `allow` (0 free only; 1 also used lately, and an enemy down to TP_ENEMY_LOW m; a point with somebody on it
        is never taken). how: 'band' / 'nearer' / 'farther' than the band (SPAWN_SPREAD band), else ''."""
        r0 = real_time()
        allp = self.with_targets(self.everybody_recent(self.now()))
        r1 = real_time()
        rows = self.rank_points(p, allp, skip, allow >= 1)
        r2 = real_time()
        self.job_ms['soldiers read'] = self.job_ms.get('soldiers read', 0.0) + (r1 - r0) * 1000.0
        self.job_ms['points ranked'] = self.job_ms.get('points ranked', 0.0) + (r2 - r1) * 1000.0
        if not rows or rows[0][0] > allow or rows[0][0] >= 2:
            return None
        best = [r for r in rows if r[0] == rows[0][0] and r[1] == rows[0][1]]
        spread = self.cs('SPAWN_SPREAD').lower()
        ne = len(self.watchers(p, allp))
        how = ''
        if spread == 'band' and ne:
            lo = float(self.ci('BAND_MIN'))
            hi = float(max(self.ci('BAND_MIN'), self.ci('BAND_MAX')))
            off = []
            for r in best:
                d = (-r[2]) ** 0.5
                o = 0.0
                if d < lo:
                    o = lo - d
                elif d > hi:
                    o = d - hi
                off.append((o, r[3], r))
            off.sort()
            inside = [x[2] for x in off if x[0] <= 0.0]
            if inside:
                best = inside
                how = 'band'
            else:
                best = [x[2] for x in off[:max(1, self.ci('SPAWN_PICK'))]]
        elif spread != 'random':
            best = best[:max(1, self.ci('SPAWN_PICK'))]
        r = best[self.rand.below(len(best))]
        k = r[4]
        self.point_used[k] = self.now()
        far = -1.0
        if ne:
            far = (-r[2]) ** 0.5
            if spread == 'band' and not how:
                how = 'nearer'
                if far > self.ci('BAND_MAX'):
                    how = 'farther'
        return (k, far, ne, r[1], how)

    def teleport(self, p, k, why, again=0, far=None):
        """Sky route (TP_ROUTE sky): straight up now, across and down in the next ticks (run_routes);
        direct: onto the point at once. The landing is checked 0.5 s later (run_teleports)."""
        pt = self.points[k]
        s = self.soldier_of(p)
        if s is None:
            return 0
        before = self.pos_of(p)
        target = (pt[1], pt[2] + self.cf('TP_UP'), pt[3])
        sky = self.cs('TP_ROUTE').lower() == 'sky' and before is not None
        first = target
        sy = 0.0
        if sky:
            sy = max(before[1], target[1]) + float(max(5, self.ci('TP_SKY')))
            first = (before[0], sy, before[2])
        self.calls = self.calls + 3
        try:
            s.setPosition(first)
        except Exception:
            self.log('teleport of %s failed: %s' % (self.name_of(p), err_text()))
            return 0
        right = None
        try:
            q = s.getPosition()
            right = (float(q[0]), float(q[1]), float(q[2]))
        except Exception:
            right = None
        t = self.now()
        self.counts['tp'] = self.counts['tp'] + 1
        self.tp_logged = self.tp_logged + 1
        loud = self.tp_logged <= 5 or why != 'spawn' or again
        if sky:
            self.tp_route[p.index] = {'k': k, 'why': why, 'again': again, 'step': 1,
                                      'at': t + max(0.05, self.cf('TP_STEP')), 'start': before, 'sy': sy,
                                      'target': target, 'loud': loud, 'far': far, 'tm': self.team_of(p)}
            if loud:
                self.log('teleport %s (%s) to %s by the sky: from %s straight up to height %.1f (reads right after '
                         '%s), then across and down to %s' % (self.name_of(p), why, pt[0], fmt_pos(before), sy,
                                                              fmt_pos(right), fmt_pos(target)))
            return 1
        try:
            s.setRotation((pt[4], 0.0, 0.0))
        except Exception:
            pass
        if loud:
            self.log('teleport %s (%s) to %s: from %s to %s, reads right after %s'
                     % (self.name_of(p), why, pt[0], fmt_pos(before), fmt_pos(target), fmt_pos(right)))
        self.landing(p, k, again, why, s, t, far)
        return 1

    def landing(self, p, k, again, why, s, t, far=None):
        self.tp_check[p.index] = [t + 0.5, k, again, why, self.health_of(s)]
        pt = self.points[k]
        self.landed[p.index] = (t, self.team_of(p), (pt[1], pt[2], pt[3]))
        g = self.cf('SPAWN_GUARD')
        if g > 0:
            self.guard[p.index] = max(self.guard.get(p.index, 0.0), t + g)
        self.life_ready(p.index, t, 'drop', self.points[k][0], far)

    def run_routes(self, t):
        for i in list(self.tp_route.keys()):
            r = self.tp_route[i]
            if t < r['at']:
                continue
            p = self.by_index(i)
            if p is None or not self.alive(p):
                del self.tp_route[i]
                continue
            root, foot = self.vehicle_root(p)
            s = self.soldier_of(p)
            q = self.pos_of(p)
            if not foot or s is None or q is None:
                del self.tp_route[i]
                continue
            tg = r['target']
            pt = self.points[r['k']]
            self.calls = self.calls + 1
            if r['step'] == 1:
                if q[1] < r['sy'] - 3.0:
                    del self.tp_route[i]
                    self.counts['tp_up_blocked'] = self.counts['tp_up_blocked'] + 1
                    what = 'left where he is'
                    if r['why'] == 'out':
                        what = 'killed (he cannot be put back)'
                    if self.counts['tp_up_blocked'] <= 10:
                        self.log('teleport of %s to %s: the way up stopped at height %.1f of %.1f (a roof over %s?) '
                                 '- %s' % (self.name_of(p), pt[0], q[1], r['sy'], fmt_pos(r['start']), what))
                    if r['why'] == 'out':
                        self.kill_now(p, 'left the arena')
                        self.counts['out_kill'] = self.counts['out_kill'] + 1
                        self.say_for(p, '[DM] %s left the arena' % self.name_of(p))
                    else:
                        self.life_ready(i, t, 'stuck', '')
                    continue
                try:
                    s.setPosition((tg[0], r['sy'], tg[2]))
                except Exception:
                    del self.tp_route[i]
                    self.log('teleport of %s: the move across failed (%s)' % (self.name_of(p), err_text()))
                    continue
                r['step'] = 2
                r['at'] = t + max(0.05, self.cf('TP_STEP'))
                continue
            d = dist2(q, tg) ** 0.5
            if d > 3.0 or abs(q[1] - r['sy']) > 4.0:
                self.counts['tp_across_short'] = self.counts['tp_across_short'] + 1
                if self.counts['tp_across_short'] <= 10:
                    self.log('teleport of %s to %s: up in the sky he stopped %.1f m short, at %s - going down from '
                             'there' % (self.name_of(p), pt[0], d, fmt_pos(q)))
            del self.tp_route[i]
            try:
                s.setPosition(tg)
            except Exception:
                self.log('teleport of %s: the move down failed (%s)' % (self.name_of(p), err_text()))
                continue
            try:
                s.setRotation((pt[4], 0.0, 0.0))
            except Exception:
                pass
            if r['loud']:
                self.log('teleport of %s to %s: across at height %.1f done, now down' % (self.name_of(p), pt[0],
                                                                                       r['sy']))
            self.landing(p, r['k'], r['again'], r['why'], s, t, r.get('far'))

    def run_teleports(self, t):
        self.picks_tick = 0
        cap = max(1, self.ci('TP_PER_TICK'))
        for i in list(self.pending_tp.keys()):
            rec = self.pending_tp[i]
            if t < rec[0]:
                continue
            if self.picks_tick >= cap:
                # nothing asked of the game for the ones over the cap: they wait a tick
                rec[0] = t + 0.05
                continue
            p = self.by_index(i)
            if p is None or not self.alive(p):
                del self.pending_tp[i]
                continue
            if len(rec) > 2:
                # waiting for a point: where he stood and the squad check are known from the first look
                here = rec[2]
                self.picks_tick = self.picks_tick + 1
                self.drop_wait(p, i, rec, here, t)
                continue
            r, foot = self.vehicle_root(p)
            if not foot:
                del self.pending_tp[i]
                continue
            here = self.pos_of(p)
            mate = None
            if here is not None:
                mate = self.leader_near(p, here, t)
            if here is not None and (mate is not None or (self.in_arena(here) and not self.drop_arena)):
                # spawned in the arena by the game, or on his squad leader anywhere: no jump
                del self.pending_tp[i]
                self.counts['in_arena_spawn'] = self.counts['in_arena_spawn'] + 1
                if mate is not None:
                    self.life_ready(i, t, 'squad', mate)
                else:
                    self.life_ready(i, t, 'game', '')
                if self.counts['in_arena_spawn'] <= 5:
                    how = 'in the arena'
                    if mate is not None:
                        how = 'next to %s (a squad spawn)' % mate
                    self.log('spawn: %s appeared %s at %s - left there' % (self.name_of(p), how, fmt_pos(here)))
                continue
            self.picks_tick = self.picks_tick + 1
            if here is not None:
                self.learn_base(p, here)
            rec.append(here)
            self.drop_wait(p, i, rec, here, t)
        for i in list(self.tp_check.keys()):
            rec = self.tp_check[i]
            if t < rec[0]:
                continue
            del self.tp_check[i]
            p = self.by_index(i)
            if p is None or not self.alive(p):
                continue
            pos = self.pos_of(p)
            k = rec[1]
            pt = self.points[k]
            if pos is None:
                continue
            d = dist2(pos, (pt[1], pt[2], pt[3])) ** 0.5
            if d > self.cf('TP_BAD'):
                self.counts['tp_bad'] = self.counts['tp_bad'] + 1
                self.point_fail[k] = self.point_fail.get(k, 0) + 1
                note = ''
                if self.point_bad(k):
                    note = ' - %s left out for this round' % pt[0]
                self.log('teleport of %s to %s did not take: %.1f m off across, at %s (point height %.2f)%s'
                         % (self.name_of(p), pt[0], d, fmt_pos(pos), pt[2], note))
                if not rec[2]:
                    pick = self.pick_point(p, 1, k)
                    if pick is not None and pick[0] != k:
                        self.teleport(p, pick[0], rec[3], 1)
                continue
            self.point_ok[k] = self.point_ok.get(k, 0) + 1
            if d > self.cf('TP_OK'):
                self.counts['tp_near'] = self.counts['tp_near'] + 1
                if self.counts['tp_near'] <= 5:
                    self.log('teleport of %s to %s landed %.1f m off, at %s - near enough'
                             % (self.name_of(p), pt[0], d, fmt_pos(pos)))
            elif self.tp_logged <= 5 or rec[2]:
                self.log('teleport of %s to %s took: %.1f m off across, standing at height %.2f (point %.2f)'
                         % (self.name_of(p), pt[0], d, pos[1], pt[2]))

    def drop_wait(self, p, i, rec, here, t):
        """Pick a point for a spawn and drop him there; no point yet: try again in 0.5 s, up to TP_GIVE_UP."""
        waited = t - rec[1]
        allow = 0
        if waited >= self.cf('TP_WAIT'):
            allow = 1
        pick = self.pick_point(p, allow)
        if pick is None:
            if waited < self.cf('TP_GIVE_UP'):
                rec[0] = t + 0.5
                if waited < 1.2:
                    self.counts['tp_wait'] = self.counts['tp_wait'] + 1
                return
            del self.pending_tp[i]
            self.life_ready(i, t, 'base', '')
            self.counts['tp_none'] = self.counts.get('tp_none', 0) + 1
            self.log('spawn: %s found no empty arena point in %.0f s - left at %s'
                     % (self.name_of(p), waited, fmt_pos(here)))
            return
        del self.pending_tp[i]
        (k, far, ne, seen, how) = pick
        if self.teleport(p, k, 'spawn', 0, far):
            fartxt = 'no enemies alive'
            if far >= 0:
                fartxt = 'nearest of %d enemies %.0f m, seen by %d' % (ne, far, seen)
                if how:
                    self.counts['band_' + how] = self.counts.get('band_' + how, 0) + 1
                    if how == 'band':
                        fartxt = fartxt + ', in the band'
                    else:
                        fartxt = fartxt + ', %s than the band' % how
                if far < self.ci('TP_ENEMY_MIN'):
                    self.counts['tp_low'] = self.counts.get('tp_low', 0) + 1
                    fartxt = fartxt + ', under %d m after waiting' % self.ci('TP_ENEMY_MIN')
            self.log('spawn: %s at %s -> %s (%s, waited %.1f s)' % (self.name_of(p), fmt_pos(here),
                                                                    self.points[k][0], fartxt, waited))

    def leader_near(self, p, here, t):
        """The name of his squad leader when he stands within 6 m (a spawn on him), or None. If the game's squad
        calls cannot be used, any team mate alive for 2 s+ within 6 m counts."""
        me = p.index
        tm = self.team_of(p)
        sq = None
        try:
            sq = int(p.getSquadId())
        except Exception:
            sq = None
        if sq is not None and sq <= 0:
            return None
        for q in self.players():
            j = q.index
            if j == me or self.team_of(q) != tm:
                continue
            if sq is not None:
                try:
                    if int(q.getSquadId()) != sq or not q.isSquadLeader():
                        continue
                except Exception:
                    continue
            elif j in self.pending_tp or j in self.tp_route or t - self.spawned_at.get(j, -100.0) < 2.0:
                continue
            if not self.alive(q):
                continue
            pq = self.pos_of(q)
            if pq is None:
                continue
            if dist2(pq, here) < 36.0 and abs(pq[1] - here[1]) < 3.0:
                return self.name_of(q)
        return None

    def run_spawn_looks(self, t):
        """Where the game spawned a soldier (no move), and how near the nearest enemy was."""
        if not self.spawn_look:
            return
        allp = None
        for i in list(self.spawn_look.keys()):
            if t < self.spawn_look[i]:
                continue
            del self.spawn_look[i]
            p = self.by_index(i)
            if p is None or not self.alive(p):
                continue
            pos = self.pos_of(p)
            if pos is None:
                continue
            if allp is None:
                allp = self.everybody_recent(t)
            d = None
            for (pq, yaw) in self.watchers(p, allp):
                dd = dist2(pos, pq) ** 0.5
                if d is None or dd < d:
                    d = dd
            self.counts['spawns'] = self.counts['spawns'] + 1
            where = 'in the arena'
            if self.arena is not None and not self.in_arena(pos):
                where = 'OUTSIDE the arena'
                self.counts['spawn_outside'] = self.counts['spawn_outside'] + 1
            if d is not None and d < 20.0:
                self.counts['spawn_enemy_20m'] = self.counts['spawn_enemy_20m'] + 1
            if d is not None and d < 10.0:
                self.counts['spawn_enemy_10m'] = self.counts['spawn_enemy_10m'] + 1
            if self.spawn_logged < self.ci('SPAWN_LOG'):
                self.spawn_logged = self.spawn_logged + 1
                dt = 'no enemy alive'
                if d is not None:
                    dt = 'nearest enemy %.0f m' % d
                self.log('spawn: %s (side %d) at %s, %s, %s' % (self.name_of(p), self.team_of(p), fmt_pos(pos),
                                                                 where, dt))

    # ------------------------------------------------------------------ pace
    def life_begin(self, p, soldier, t, ready):
        """A life starts at the spawn; it is timed from the drop (or the spawn, when nobody moves him)."""
        if not self.ci('PACE'):
            return
        L = {'spawn': t, 'ready': None, 'how': '', 'pt': '', 'd0': None, 'hit': None, 'frag': None,
             'near': None, 'hp': None, 's': soldier, 'name': self.name_of(p)}
        self.lives[p.index] = L
        if ready:
            self.life_ready(p.index, t, 'game', '')

    def life_ready(self, i, t, how, where, far=None):
        """He is where he fights from: dropped at a point, or left where the game put him."""
        L = self.lives.get(i)
        if L is None:
            return
        if L['hit'] is not None or L['frag'] is not None:
            return
        L['ready'] = t
        L['how'] = how
        L['pt'] = where
        L['d0'] = None
        L['near'] = None
        L['hp'] = None
        if far is not None and far >= 0:
            L['d0'] = far
        elif far is not None:
            L['d0'] = -1.0

    def life_mark(self, i, what, t):
        L = self.lives.get(i)
        if L is None or L['ready'] is None or L[what] is not None:
            return
        L[what] = t

    def run_pace(self, t):
        """Every 0.5 s: health going down; the nearest enemy at the start of a life (a drop has it from the
        pick), an enemy within PACE_NEAR m (PACE_NEAR 0: not watched). The places come from everybody_recent,
        read again about once a second (~8 calls a living soldier)."""
        allp = None
        near = float(self.ci('PACE_NEAR'))
        for i in list(self.lives.keys()):
            L = self.lives[i]
            if L['ready'] is None:
                if t - L['spawn'] > 20.0:
                    L['ready'] = t
                    L['how'] = 'late'
                continue
            if t < L['ready']:
                continue
            if L['d0'] is None or (L['near'] is None and near > 0.0):
                if allp is None:
                    allp = self.everybody_recent(t)
                me = None
                tm = 0
                for (j, tj, pq, yaw) in allp:
                    if j == i:
                        me = pq
                        tm = tj
                        break
                if me is not None:
                    d = -1.0
                    for (j, tj, pq, yaw) in allp:
                        if j == i or (self.mode == 'tdm' and tj == tm):
                            continue
                        dd = dist2(me, pq) ** 0.5
                        if d < 0.0 or dd < d:
                            d = dd
                    if L['d0'] is None:
                        L['d0'] = d
                    if L['near'] is None and d >= 0.0 and d <= near and near > 0.0:
                        L['near'] = t
            if L['hit'] is None:
                h = self.health_of(L['s'])
                self.calls = self.calls + 1
                if h is not None:
                    if L['hp'] is not None and h < L['hp'] - 0.5:
                        L['hit'] = t
                    L['hp'] = h

    def life_end(self, i, t, how):
        L = self.lives.get(i)
        if L is None:
            return
        del self.lives[i]
        if L['ready'] is None:
            self.pace_early = self.pace_early + 1
            return
        r = L['ready']
        life = t - r
        met = t
        for k in ('hit', 'frag'):
            if L[k] is not None and L[k] < met:
                met = L[k]
        rel = []
        for k in ('hit', 'frag', 'near'):
            if L[k] is None:
                rel.append(None)
            else:
                rel.append(max(0.0, L[k] - r))
        d0 = L['d0']
        if d0 is None:
            d0 = -1.0
        self.pace.append((life, d0, max(0.0, met - r), rel[0], rel[1], rel[2], L['how']))
        if self.pace_logged < self.ci('PACE_LOG'):
            self.pace_logged = self.pace_logged + 1
            src = {'drop': 'dropped at %s' % L['pt'], 'game': 'spawned by the game', 'squad':
                   'spawned on %s' % L['pt'], 'base': 'left at the base', 'stuck': 'not moved (roof)',
                   'late': 'not moved'}.get(L['how'], L['how'])
            e = 'no enemy alive'
            if d0 >= 0.0:
                e = 'nearest enemy %.0f m' % d0
            parts = []
            for (k, v) in (('enemy within %d m' % self.ci('PACE_NEAR'), rel[2]), ('first hit taken', rel[0]),
                           ('first frag', rel[1])):
                if v is None:
                    parts.append('%s -' % k)
                else:
                    parts.append('%s %.1f s' % (k, v))
            self.log('life: %s %.1f s, %s, %s; %s; %s' % (L['name'], life, src, e, ', '.join(parts), how))

    def pace_summary(self):
        lv = self.pace
        n = len(lv)
        if not n:
            if self.lives or self.pace_early:
                self.log('  pace: no life ended after its drop (%d still going, %d died before)'
                         % (len(self.lives), self.pace_early))
            return
        def q(vals, f):
            v = vals[:]
            v.sort()
            if not v:
                return None
            return v[int(f * (len(v) - 1) + 0.5)]
        def q3(vals):
            if not vals:
                return '-'
            return '%.0f s (%.0f-%.0f)' % (q(vals, 0.5), q(vals, 0.25), q(vals, 0.75))
        lifes = [x[0] for x in lv]
        mets = [x[2] for x in lv]
        hits = [x[3] for x in lv if x[3] is not None]
        frags = [x[4] for x in lv if x[4] is not None]
        nears = [x[5] for x in lv if x[5] is not None]
        quick = len([m for m in mets if m <= 15.0])
        early = len([x for x in lv if x[0] <= 5.0])
        mins = (self.now() - self.t0) / 60.0
        if mins < 0.1:
            mins = 0.1
        self.log('  pace: %d lives (%.1f a minute; %d still going, %d died before the drop); a life %s; first '
                 'contact (hit taken, frag or death) %s, within 15 s %d%%; died within 5 s %d'
                 % (n, n / mins, len(self.lives), self.pace_early, q3(lifes), q3(mets), (100 * quick) / n, early))
        nt = ''
        if self.ci('PACE_NEAR') > 0:
            nt = 'enemy within %d m %s (%d lives); ' % (self.ci('PACE_NEAR'), q3(nears), len(nears))
        self.log('  pace: %sfirst hit taken %s (%d lives); first frag %s (%d)'
                 % (nt, q3(hits), len(hits), q3(frags), len(frags)))
        d0s = [x[1] for x in lv if x[1] >= 0.0]
        if d0s:
            rows = []
            for (lo, hi) in ((0, 25), (25, 35), (35, 45), (45, 80), (80, 100), (100, 100000)):
                g = [x for x in lv if lo <= x[1] < hi]
                if not g:
                    continue
                name = '%d-%d m' % (lo, hi)
                if hi > 1000:
                    name = '%d+ m' % lo
                gm = [x[2] for x in g]
                rows.append('%s: %d, contact %.0f s, died within 5 s %d'
                            % (name, len(g), q(gm, 0.5), len([x for x in g if x[0] <= 5.0])))
            self.log('  pace: nearest enemy at the start %s (median); ' % q3(d0s).replace(' s', ' m') + '; '.join(rows))
        hows = {}
        for x in lv:
            hows[x[6]] = hows.get(x[6], 0) + 1
        keys = list(hows.keys())
        keys.sort()
        self.log('  pace: lives started by ' + ', '.join(['%s %d' % (k, hows[k]) for k in keys]))

    def run_guard(self, t):
        """Spawn protection: health held full for SPAWN_GUARD s after a spawn or a move."""
        if not self.guard:
            return
        mx = float(self.ci('HP_MAX'))
        for i in list(self.guard.keys()):
            if t > self.guard[i]:
                del self.guard[i]
                continue
            p = self.by_index(i)
            if p is None:
                del self.guard[i]
                continue
            # no alive / vehicle calls: a dead or downed soldier reads 0 (or cannot be read)
            s = self.soldier_of(p)
            if s is None:
                continue
            h = self.health_of(s)
            if h is None or h <= 0 or h >= mx:
                continue
            self.set_health(s, mx)
            self.counts['guard_hp'] = self.counts['guard_hp'] + 1
            rec = self.tp_check.get(i)
            if not (rec is not None and rec[4] is not None and h < rec[4] - 0.5):
                self.life_mark(i, 'hit', t)
            if rec is not None and rec[4] is not None and h < rec[4] - 0.5:
                self.counts['tp_hurt'] = self.counts['tp_hurt'] + 1
                if self.counts['tp_hurt'] <= 5:
                    self.log('%s lost health landing after a move: %.0f -> %.0f (had %.0f up in the sky)'
                             % (self.name_of(p), h, mx, rec[4]))
            elif self.counts['guard_hp'] <= 5:
                self.log('spawn protection: %s health %.0f -> %.0f, %.1f s after his spawn'
                         % (self.name_of(p), h, mx, t - self.spawned_at.get(i, t)))

    def border_on(self):
        return self.cs('OUT_ACTION').lower() in ('kill', 'tp') or self.cs('OUT_BOTS').lower() in ('kill', 'tp')

    def check_arena(self, t):
        if not self.border_on():
            return
        grace = self.cf('OUT_GRACE')
        for p in self.players():
            i = p.index
            if i in self.pending_tp or i in self.tp_check or i in self.tp_route:
                continue
            if t - self.spawned_at.get(i, -100.0) < grace:
                continue
            if not self.alive(p):
                if i in self.out_since:
                    del self.out_since[i]
                continue
            pos = self.pos_of(p)
            if pos is None:
                continue
            if self.in_arena(pos):
                if i in self.out_since:
                    del self.out_since[i]
                    self.log('%s is back in the arena' % self.name_of(p))
                continue
            bot = self.is_bot(p)
            act = self.cs('OUT_ACTION')
            if bot:
                act = self.cs('OUT_BOTS')
            if act not in ('kill', 'tp'):
                continue
            if i in self.kill_on_exit:
                continue
            if i not in self.out_since:
                self.out_since[i] = t
                self.say_for(p, '[DM] %s: back into the arena - %d s' % (self.name_of(p), self.ci('OUT_TIME')))
                self.log('%s left the arena at (%.1f, %.1f, %.1f)' % (self.name_of(p), pos[0], pos[1], pos[2]))
                continue
            if t - self.out_since[i] < self.ci('OUT_TIME'):
                continue
            del self.out_since[i]
            r, foot = self.vehicle_root(p)
            pick = None
            if act == 'tp' and foot and self.points:
                pick = self.pick_point(p, 1)
            if pick is not None:
                k = pick[0]
                self.teleport(p, k, 'out')
                self.counts['out_tp'] = self.counts['out_tp'] + 1
                self.log('%s put back into the arena at %s' % (self.name_of(p), self.points[k][0]))
            elif act == 'kill' or act == 'tp':
                if foot:
                    self.kill_now(p, 'left the arena')
                    self.counts['out_kill'] = self.counts['out_kill'] + 1
                    self.say_for(p, '[DM] %s left the arena' % self.name_of(p))
                elif i not in self.in_veh:
                    self.kill_on_exit[i] = 1
                    self.break_vehicle(p, r, 'outside the arena')

    def kill_now(self, p, why):
        s = self.soldier_of(p)
        if s is None:
            return 0
        self.script_kill[p.index] = self.now()
        ok = self.set_health(s, 0)
        self.log('%s killed: %s%s' % (self.name_of(p), why, ['', ' (FAILED)'][not ok]))
        return ok

    def run_kills(self, t):
        for i in list(self.pending_kill.keys()):
            rec = self.pending_kill[i]
            if t < rec[0]:
                continue
            p = self.by_index(i)
            if p is None or not self.alive(p):
                del self.pending_kill[i]
                continue
            r, foot = self.vehicle_root(p)
            if not foot:
                rec[0] = t + 0.5
                rec[2] = rec[2] + 1
                if rec[2] > 20:
                    del self.pending_kill[i]
                continue
            del self.pending_kill[i]
            if self.kill_now(p, rec[1]):
                self.counts['veh_kill'] = self.counts['veh_kill'] + 1
                self.say_for(p, '[DM] %s killed: %s' % (self.name_of(p), rec[1]))

    def run_vehicles(self, t):
        g = self.ci('VEH_GRACE')
        for i in list(self.in_veh.keys()):
            rec = self.in_veh[i]
            if rec['done'] or t - rec['since'] < g:
                continue
            rec['done'] = 1
            p = self.by_index(i)
            if p is None or not self.alive(p):
                del self.in_veh[i]
                continue
            r, foot = self.vehicle_root(p)
            if foot:
                del self.in_veh[i]
                continue
            self.kill_on_exit[i] = 1
            self.break_vehicle(p, r, 'stayed in a vehicle')

    def break_vehicle(self, p, root, why):
        name = self.tpl(root)
        hp = self.ci('VEH_HP')
        done = 0
        before = None
        if root is not None and hasattr(root, 'setDamage'):
            try:
                before = root.getDamage()
            except Exception:
                before = None
            try:
                root.setDamage(hp)
                done = 1
            except Exception:
                done = 0
        self.calls = self.calls + 2
        if done:
            self.counts['veh_hp'] = self.counts['veh_hp'] + 1
            self.say_for(p, '[DM] %s %s: it is wrecked, and he dies when he gets out' % (self.name_of(p), why))
            self.log('%s %s %s: health %s -> %d' % (self.name_of(p), why, name, before, hp))
        else:
            self.say_for(p, '[DM] %s %s: he dies when he gets out, his frags do not count' % (self.name_of(p), why))
            self.log('%s %s %s: the vehicle has no health calls - killed when he gets out' % (self.name_of(p),
                                                                                             why, name))

    def run_hp(self, t):
        if not self.hp_q:
            return
        keep = []
        for rec in self.hp_q:
            (at, i, add, stage) = rec
            if t < at:
                keep.append(rec)
                continue
            p = self.by_index(i)
            if p is None or not self.alive(p):
                continue
            r, foot = self.vehicle_root(p)
            if not foot:
                continue
            s = self.soldier_of(p)
            if s is None:
                continue
            h = self.health_of(s)
            if h is None or h <= 1:
                continue
            mx = float(self.ci('HP_MAX'))
            if stage == 0:
                want = h + add
                if want > mx:
                    want = mx
                if want <= h:
                    continue
                if self.ci('HP_NUDGE'):
                    self.set_health(s, want - 1)
                    keep.append((t + 0.1, i, want, 1))
                else:
                    self.set_health(s, want)
                self.counts['hp'] = self.counts['hp'] + 1
                if self.counts['hp'] <= 3:
                    self.log('health for the frag: %s %.0f -> %.0f' % (self.name_of(p), h, want))
            else:
                if h < add:
                    self.set_health(s, add)
        self.hp_q = keep

    def run_tts(self, t):
        """A dead player's time to spawn, read every 0.25 s until the game has set it (it reads 0 right after
        the death): cut down to RESPAWN when it is longer."""
        for i in list(self.tts_q.keys()):
            rec = self.tts_q[i]
            if t < rec[0]:
                continue
            p = self.by_index(i)
            if p is None or t > rec[1]:
                del self.tts_q[i]
                continue
            want = self.ci('RESPAWN')
            self.calls = self.calls + 1
            try:
                old = float(p.getTimeToSpawn())
            except Exception:
                del self.tts_q[i]
                if not self.tts_checked:
                    self.tts_checked = 1
                    self.log('time to spawn: cannot read (%s)' % err_text())
                continue
            if old <= want + 0.05:
                rec[0] = t + 0.25
                continue
            del self.tts_q[i]
            self.calls = self.calls + 2
            try:
                p.setTimeToSpawn(want)
                self.counts['tts_cut'] = self.counts.get('tts_cut', 0) + 1
                if self.tts_logged < 3:
                    self.tts_logged = self.tts_logged + 1
                    self.log('time to spawn of %s: %.1f -> %s (reads %s)' % (self.name_of(p), old, want,
                                                                            p.getTimeToSpawn()))
            except Exception:
                if self.tts_logged < 3:
                    self.tts_logged = self.tts_logged + 1
                    self.log('time to spawn: cannot set (%s)' % err_text())

    # ------------------------------------------------------------------ endless magazines
    def want_mags(self, name):
        if not self.ci('INF_MAGS') or not name:
            return 0
        low = name.lower()
        for w in self.cs('INF_SKIP').split():
            if w and w.lower() in low:
                return 0
        return 1

    def mags_for(self, weapon):
        if weapon is None or not self.ci('INF_MAGS'):
            return
        try:
            name = str(weapon.templateName)
        except Exception:
            return
        if not name or name in self.mags_old or name in self.mags_q:
            return
        if not self.want_mags(name):
            self.mags_old[name] = None
            return
        self.mags_q.append(name)

    def run_mags(self):
        n = 0
        while self.mags_q and n < 3:
            name = self.mags_q.pop(0)
            n = n + 1
            if name in self.mags_old:
                continue
            want = min(500, max(1, self.ci('MAGS')))
            self.rcon('ObjectTemplate.activeSafe GenericFireArm %s' % name)
            old = self.rcon('ObjectTemplate.ammo.nrOfMags')
            w = old.split()
            val = -1.0
            if w:
                val = to_float(w[0], -1.0)
            if val < 0 or 'rror' in old or 'nknown' in old:
                self.mags_old[name] = None
                self.log('endless magazines: %s left alone (nrOfMags reads "%s")' % (name, old))
                continue
            if int(val) == want and name not in self.mags_old:
                # the read is the last changed gun's: the template was not made active
                self.mags_old[name] = None
                self.log('endless magazines: %s left alone (it did not become the active template)' % name)
                continue
            self.rcon('ObjectTemplate.ammo.nrOfMags %d' % want)
            back = self.rcon('ObjectTemplate.ammo.nrOfMags')
            self.mags_old[name] = w[0]
            self.log('endless magazines: %s nrOfMags %s -> %d (reads %s) - from the next spawn' % (name, w[0],
                                                                                                 want, back))

    def mags_back(self):
        done = 0
        for name in list(self.mags_old.keys()):
            old = self.mags_old[name]
            if old is None:
                continue
            self.rcon('ObjectTemplate.activeSafe GenericFireArm %s' % name)
            self.rcon('ObjectTemplate.ammo.nrOfMags %s' % old)
            done = done + 1
        if done:
            self.log('endless magazines: %d guns back to their own nrOfMags' % done)
        self.mags_old = {}
        self.mags_q = []

    # ------------------------------------------------------------------ scores
    def run_fix(self):
        if not self.fix:
            return
        if not self.ci('SCORE_IS_FRAGS'):
            self.fix = {}
            return
        todo = list(self.fix.keys())
        self.fix = {}
        for i in todo:
            p = self.by_index(i)
            if p is None:
                continue
            f = self.frags.get(i, 0)
            k = self.kills.get(i, 0)
            self.calls = self.calls + 2
            try:
                sc = p.score
                if sc.score != f:
                    sc.score = f
                    self.counts['score_set'] = self.counts['score_set'] + 1
                if sc.kills != k:
                    sc.kills = k
                if not self.score_checked and (f or k):
                    self.score_checked = 1
                    self.log('scoreboard: %s score %s kills %s (wanted %d / %d)' % (self.name_of(p), sc.score,
                                                                                    sc.kills, f, k))
            except Exception:
                if not self.score_checked:
                    self.score_checked = 1
                    self.log('scoreboard: cannot set (%s)' % err_text())

    # ------------------------------------------------------------------ drops
    def drop_mode(self):
        m = self.cs('DROP_MODE').lower()
        if m not in ('bags', 'crate', 'spawner', 'off'):
            m = 'bags'
        return m

    def drop_items(self, mode):
        if mode == 'crate':
            return [self.cs('CRATE')]
        out = []
        for k in range(max(0, self.ci('DROP_MED'))):
            out.append(self.cs('MED_BAG'))
        for k in range(max(0, self.ci('DROP_AMMO'))):
            out.append(self.cs('AMMO_BAG'))
        # mix them round the body: med, ammo, med, ammo ...
        med = [x for x in out if x == self.cs('MED_BAG')]
        amm = [x for x in out if x != self.cs('MED_BAG')]
        mixed = []
        while med or amm:
            if med:
                mixed.append(med.pop())
            if amm:
                mixed.append(amm.pop())
        return mixed

    def run_drops(self, t):
        if not self.drops_q:
            return
        made = 0
        while self.drops_q and made < 1:
            (at, pos, team, vname) = self.drops_q.pop(0)
            self.make_drop(pos, team, vname)
            made = made + 1

    def spawner_for(self, name):
        """Our own ObjectSpawner template for a bag template (made once a server run). Test way only."""
        if name in self.spawners:
            return self.spawners[name]
        sp = 'fldm_sp_%d' % (len(self.spawners) + 1)
        lines = ['ObjectTemplate.create ObjectSpawner %s' % sp,
                 'ObjectTemplate.activeSafe ObjectSpawner %s' % sp,
                 'ObjectTemplate.isNotSaveable 1',
                 'ObjectTemplate.hasMobilePhysics 0',
                 'ObjectTemplate.setObjectTemplate 1 %s' % name,
                 'ObjectTemplate.setObjectTemplate 2 %s' % name,
                 'ObjectTemplate.minSpawnDelay 0',
                 'ObjectTemplate.maxSpawnDelay 0',
                 'ObjectTemplate.maxNrOfObjectSpawned 1']
        ans = []
        for ln in lines:
            a = self.rcon(ln)
            if a:
                ans.append('%s -> "%s"' % (ln, a))
        if not ans:
            ans = ['no answers']
        self.log('spawner template %s for %s: %s' % (sp, name, '; '.join(ans)))
        self.spawners[name] = sp
        return sp

    def make_drop(self, pos, team, vname, mode=None, test=0):
        if mode is None:
            mode = self.drop_mode()
        items = self.drop_items(mode)
        if not items:
            return (0, 0, 0)
        if mode == 'crate' and self.ci('CRATE_FAST'):
            self.crate_fast(1)
        detail = test or self.drops_logged < self.ci('DROP_LOG')
        rad = self.cf('DROP_RADIUS')
        up = self.cf('DROP_UP')
        n = len(items)
        step = 12 // n
        if step < 1:
            step = 1
        start = self.rand.below(12)
        tpls = {}
        made = []
        answers = []
        for k in range(n):
            d = DIRS[(start + k * step) % 12]
            r = rad
            if n == 1:
                r = 0.0
            x = pos[0] + d[0] * r
            y = pos[1] + up
            z = pos[2] + d[1] * r
            name = items[k]
            if name not in tpls:
                tpls[name] = self.objects_of(name)
            what = name
            if mode == 'spawner':
                what = self.spawner_for(name)
            a1 = self.rcon('Object.create %s' % what)
            a2 = self.rcon('Object.absolutePosition %.2f/%.2f/%.2f' % (x, y, z))
            a3 = self.rcon('Object.layer 1')
            a4 = '-'
            if team in (1, 2) and mode != 'crate':
                a4 = self.rcon('Object.team %d' % team)
            if detail:
                a5 = self.rcon('Object.absolutePosition')
                answers.append('%s at %.2f/%.2f/%.2f: create "%s", position "%s", layer "%s", team "%s", '
                               'position reads "%s"' % (what, x, y, z, a1, a2, a3, a4, a5))
            made.append((name, (x, y, z)))
            if name not in self.made_first:
                self.made_first[name] = 1
                self.log('first %s this round (%s): Object.create answered "%s"' % (name, mode, a1))
        near, far = self.find_new(tpls, pos, rad, 1)
        self.counts['made'] = self.counts['made'] + near
        if near < len(made):
            self.counts['made_bad'] = self.counts['made_bad'] + len(made) - near
        if detail:
            self.drops_logged = self.drops_logged + 1
            for a in answers:
                self.log('  ' + a)
            totals = ', '.join(['%s %d before' % (nm, len(tpls[nm])) for nm in list(tpls.keys())])
            self.log('drop (%s) for %s at %s: %d made, the server lists %d new near (within %.1f m), %d new farther '
                     '(%s)' % (mode, vname, fmt_pos(pos), len(made), near, rad + 2.0, far, totals))
            snap = {}
            for nm in list(tpls.keys()):
                snap[nm] = tpls[nm]
            t = self.now()
            self.drop_checks.append([t + 1.0, snap, pos, mode, vname, '1 s'])
            self.drop_checks.append([t + 3.0, snap, pos, mode, vname, '3 s'])
        elif near < len(made):
            self.log('drop (%s) for %s at %s: %d made, %d seen near' % (mode, vname, fmt_pos(pos), len(made), near))
        mx = max(0, self.ci('DROP_MAX'))
        while len(self.drops) > mx:
            self.take_away(self.drops.pop(0), 'too many')
        return (len(made), near, far)

    def find_new(self, tpls, pos, rad, track):
        """New objects of the templates since the snapshot: (near, far); near ones are tracked for removal."""
        near = 0
        far = 0
        for name in list(tpls.keys()):
            before = tpls[name]
            after = self.objects_of(name)
            for key in list(after.keys()):
                o = after[key]
                if key in before or key in self.seen_objs:
                    continue
                try:
                    q = o.getPosition()
                    q = (float(q[0]), float(q[1]), float(q[2]))
                except Exception:
                    q = None
                if q is None or dist2(q, pos) > (rad + 2.0) * (rad + 2.0):
                    far = far + 1
                    if far <= 6:
                        self.log('  new %s farther away: at %s' % (name, fmt_pos(q)))
                    continue
                near = near + 1
                if track:
                    self.seen_objs[key] = 1
                    self.drops.append([self.now(), o, q, name])
        return (near, far)

    def run_drop_checks(self, t):
        if not self.drop_checks:
            return
        keep = []
        for rec in self.drop_checks:
            if t < rec[0]:
                keep.append(rec)
                continue
            (at, snap, pos, mode, vname, when) = rec
            parts = []
            for name in list(snap.keys()):
                now_objs = self.objects_of(name)
                new = []
                for key in list(now_objs.keys()):
                    if key in snap[name]:
                        continue
                    try:
                        q = now_objs[key].getPosition()
                        q = (float(q[0]), float(q[1]), float(q[2]))
                        new.append('%s %.1f m' % (fmt_pos(q), dist3(q, pos)))
                    except Exception:
                        new.append('? place')
                parts.append('%s: %d listed, %d new [%s]' % (name, len(now_objs), len(new), '; '.join(new[:6])))
            self.log('drop (%s) for %s, %s later: %s' % (mode, vname, when, ' | '.join(parts)))
        self.drop_checks = keep

    def objects_of(self, name):
        self.calls = self.calls + 1
        res = {}
        try:
            for o in bf2.objectManager.getObjectsOfTemplate(name):
                res[id(o)] = o
        except Exception:
            pass
        return res

    def expire_drops(self, t):
        life = self.ci('DROP_LIFE')
        keep = []
        lists = {}
        for rec in self.drops:
            if t - rec[0] < life:
                keep.append(rec)
                continue
            name = rec[3]
            if name not in lists:
                lists[name] = self.objects_of(name)
            if id(rec[1]) not in lists[name]:
                self.counts['gone'] = self.counts['gone'] + 1
                if id(rec[1]) in self.seen_objs:
                    del self.seen_objs[id(rec[1])]
                continue
            self.take_away(rec, 'old')
        self.drops = keep

    def take_away(self, rec, why):
        o = rec[1]
        key = id(o)
        if key in self.seen_objs:
            del self.seen_objs[key]
        try:
            q = o.getPosition()
            q = (float(q[0]), float(q[1]), float(q[2]))
        except Exception:
            return
        if dist3(q, rec[2]) > 3.0:
            # the game gave the object to something else (a thrown bag): leave it
            self.counts['gone'] = self.counts['gone'] + 1
            return
        self.calls = self.calls + 2
        try:
            o.setPosition((q[0], q[1] - 1000.0, q[2]))
            self.counts['removed'] = self.counts['removed'] + 1
        except Exception:
            self.log('cannot take a %s away: %s' % (rec[3], err_text()))

    # ------------------------------------------------------------------ the refill crate
    def refill_on(self):
        return self.cs('REFILL').lower() == 'crate'

    def run_refill(self, t):
        if self.refill_q:
            keep = []
            made = 0
            for rec in self.refill_q:
                if t < rec[0] or made >= 2:
                    keep.append(rec)
                    continue
                made = made + 1
                self.make_refill(rec[1], t)
            self.refill_q = keep
        if self.crates:
            for c in self.crates:
                if c['state'] == 'live' and t >= c['until']:
                    self.remove_crate(c, 'its time is up')
            self.crates = [c for c in self.crates if c['state'] != 'gone']

    def crates_near(self, name, spot, rad):
        res = []
        self.calls = self.calls + 1
        try:
            objs = bf2.objectManager.getObjectsOfTemplate(name)
        except Exception:
            return res
        for o in objs:
            try:
                q = o.getPosition()
                q = (float(q[0]), float(q[1]), float(q[2]))
            except Exception:
                continue
            if dist3(q, spot) <= rad:
                res.append((o, q))
        return res

    def make_refill(self, ai, t):
        p = self.by_index(ai)
        if p is None or not self.alive(p):
            return
        r, foot = self.vehicle_root(p)
        if not foot:
            return
        pos = self.pos_of(p)
        if pos is None:
            return
        life = max(0.2, self.cf('REFILL_LIFE'))
        for c in self.crates:
            if c['ai'] == ai and c['state'] == 'live' and t - c['t'] < 0.6:
                c['until'] = t + life
                self.counts['refill_more'] = self.counts['refill_more'] + 1
                return
        name = self.cs('CRATE')
        if self.ci('CRATE_FAST'):
            self.crate_fast(1)
        d = DIRS[self.rand.below(12)]
        off = self.cf('REFILL_OFFSET')
        spot = (pos[0] + d[0] * off, pos[1] - 1.0 + 0.3, pos[2] + d[1] * off)
        detail = self.refills_logged < self.ci('REFILL_LOG')
        for c in self.crates:
            if c['state'] == 'parked' and c['obj'] is not None:
                try:
                    c['obj'].setPosition(spot)
                except Exception:
                    c['state'] = 'gone'
                    continue
                c['state'] = 'live'
                c['kind'] = 'refill'
                c['t'] = t
                c['until'] = t + life
                c['ai'] = ai
                c['spot'] = spot
                self.counts['refill'] = self.counts['refill'] + 1
                self.counts['refill_reused'] = self.counts['refill_reused'] + 1
                if detail:
                    self.refills_logged = self.refills_logged + 1
                    self.log('refill for %s: a parked crate brought to %s' % (self.name_of(p), fmt_pos(spot)))
                return
        live = [c for c in self.crates if c['state'] != 'gone' and c.get('kind') != 'arena']
        while len(live) >= max(1, self.ci('REFILL_MAX')):
            c = live.pop(0)
            self.remove_crate(c, 'too many', 1)
        self.crates = [c for c in self.crates if c['state'] != 'gone']
        n0 = len(self.crates_near(name, spot, 3.0))
        a1 = self.rcon('Object.create %s' % name)
        a2 = self.rcon('Object.absolutePosition %.2f/%.2f/%.2f' % (spot[0], spot[1], spot[2]))
        a3 = self.rcon('Object.layer 1')
        oid = ''
        w = a1.split()
        if w and w[0].lower().startswith('id'):
            oid = w[0]
        near = self.crates_near(name, spot, 3.0)
        obj = None
        if len(near) > n0:
            best = None
            for (o, q) in near:
                dd = dist3(q, spot)
                if best is None or dd < best:
                    best = dd
                    obj = o
        else:
            self.counts['refill_unseen'] = self.counts['refill_unseen'] + 1
        self.crates.append({'t': t, 'until': t + life, 'oid': oid, 'ai': ai, 'spot': spot, 'name': name,
                            'obj': obj, 'state': 'live'})
        self.counts['refill'] = self.counts['refill'] + 1
        if detail:
            self.refills_logged = self.refills_logged + 1
            seen = 'yes'
            if obj is None:
                seen = 'NO'
            self.log('refill for %s at %s: %s at %s - create "%s", position "%s", layer "%s"; the server lists it '
                     'there: %s' % (self.name_of(p), fmt_pos(pos), name, fmt_pos(spot), a1, a2, a3, seen))

    def remove_crate(self, c, why, quiet=0):
        """Object.delete by the id Object.create gave; a crate still there is parked in the sky."""
        if c.get('sp_oid') and self.delete_works:
            self.rcon('Object.active %s' % c['sp_oid'])
            self.rcon('Object.delete')
            c['sp_oid'] = ''
        if c.get('find'):
            del c['find']
        if c['obj'] is None and c.get('spawner'):
            c['state'] = 'gone'     # its crate was never found: nothing of ours to take away
            return
        name = c['name']
        spot = c['spot']
        ans = 'no id'
        before = self.crates_near(name, spot, 3.0)
        if self.ci('REFILL_DELETE') and self.delete_works and c['oid']:
            a1 = self.rcon('Object.active %s' % c['oid'])
            a2 = self.rcon('Object.delete')
            ans = 'Object.active %s "%s", Object.delete "%s"' % (c['oid'], a1, a2)
        after = self.crates_near(name, spot, 3.0)
        if c['obj'] is not None:
            # the game keeps one Python object per game object: is ours still listed (wherever it lies)?
            left = [x for x in self.crates_near(name, spot, 1e9) if x[0] is c['obj']]
        elif len(after) < len(before):
            left = []
        else:
            left = after
        detail = self.removals_logged < self.ci('REFILL_LOG') and not quiet
        if not left:
            c['state'] = 'gone'
            self.counts['refill_deleted'] = self.counts['refill_deleted'] + 1
            if detail:
                self.removals_logged = self.removals_logged + 1
                self.log('refill crate at %s taken away (%s): %s; nothing left there' % (fmt_pos(spot), why, ans))
            return
        if c['oid'] and self.ci('REFILL_DELETE') and self.delete_works:
            self.delete_works = 0
            self.log('refill crate at %s: Object.delete did not take it away (%s) - from now on crates are parked '
                     '%d m up and used again' % (fmt_pos(spot), ans, self.ci('REFILL_SKY')))
        if c['obj'] is None:
            c['obj'] = left[0][0]
        up = float(self.ci('REFILL_SKY'))
        try:
            q = c['obj'].getPosition()
            c['obj'].setPosition((float(q[0]), float(q[1]) + up, float(q[2])))
            c['state'] = 'parked'
            c['parked_at'] = self.now()
            c['spot'] = (float(q[0]), float(q[1]) + up, float(q[2]))
            c['ground'] = float(q[1])
            self.counts['refill_parked'] = self.counts['refill_parked'] + 1
        except Exception:
            c['state'] = 'gone'
            self.log('refill crate at %s: cannot move it (%s)' % (fmt_pos(spot), err_text()))
            return
        if detail:
            self.removals_logged = self.removals_logged + 1
            self.log('refill crate at %s (%s): %s; parked %d m up' % (fmt_pos(spot), why, ans, int(up)))

    def lift_parked(self):
        """A parked crate falls: lifted again before it comes down (each second)."""
        up = float(self.ci('REFILL_SKY'))
        tn = self.now()
        for c in self.crates:
            if c['state'] != 'parked' or c['obj'] is None:
                continue
            if c.get('kind') in ('arena', 'test') and tn - c.get('parked_at', tn) > 420.0:
                c['state'] = 'gone'     # the game takes a supply crate away after about 5 minutes
                continue
            self.calls = self.calls + 1
            try:
                q = c['obj'].getPosition()
                q = (float(q[0]), float(q[1]), float(q[2]))
            except Exception:
                c['state'] = 'gone'
                continue
            if q[1] < c.get('ground', q[1]) + up * 0.5:
                try:
                    c['obj'].setPosition((q[0], q[1] + up * 0.5, q[2]))
                    self.counts['refill_lifted'] = self.counts['refill_lifted'] + 1
                except Exception:
                    c['state'] = 'gone'
        self.crates = [c for c in self.crates if c['state'] != 'gone']

    def clear_crates(self):
        for c in self.crates:
            if c['state'] == 'live':
                self.remove_crate(c, 'the round ended', 1)
        self.crates = [c for c in self.crates if c['state'] == 'parked']

    # ------------------------------------------------------------------ ammo crates spread over the arena
    def crate_arena_tpl(self, on):
        """While arena crates are out: the crate template heals ARENA_CRATE_HEAL (0 = not at all) and refills
        ammo at ARENA_CRATE_AMMO ('' = its own speed); put back when they are taken in."""
        name = self.cs('CRATE')
        amm = self.cs('ARENA_CRATE_AMMO').strip()
        if on and not self.ac_tpl:
            self.rcon('ObjectTemplate.activeSafe SupplyObject %s' % name)
            r = self.rcon('ObjectTemplate.refillAmmoSpeed')
            h = self.rcon('ObjectTemplate.healSpeed')
            if self.crate_changed:
                self.ac_tpl_old = self.crate_old
            else:
                old_r = '7'
                old_h = '3'
                if r and to_float(r.split()[0], -1.0) >= 0:
                    old_r = r.split()[0]
                if h and to_float(h.split()[0], -1.0) >= 0:
                    old_h = h.split()[0]
                self.ac_tpl_old = (old_r, old_h)
            heal = str(max(0, self.ci('ARENA_CRATE_HEAL')))
            a2 = self.rcon('ObjectTemplate.healSpeed %s' % heal)
            a1 = ''
            if amm:
                a1 = self.rcon('ObjectTemplate.refillAmmoSpeed %s' % amm)
            self.ac_tpl = 1
            self.log('arena crates: %s healSpeed %s -> %s ("%s"), refillAmmoSpeed %s%s; reads %s / %s'
                     % (name, h, heal, a2, r, (amm and ' -> %s ("%s")' % (amm, a1)) or ' (its own)',
                        self.rcon('ObjectTemplate.healSpeed'), self.rcon('ObjectTemplate.refillAmmoSpeed')))
        elif not on and self.ac_tpl:
            self.rcon('ObjectTemplate.activeSafe SupplyObject %s' % name)
            if self.crate_changed:
                self.rcon('ObjectTemplate.healSpeed 100')
                if amm:
                    self.rcon('ObjectTemplate.refillAmmoSpeed 1000')
            else:
                self.rcon('ObjectTemplate.healSpeed %s' % self.ac_tpl_old[1])
                if amm:
                    self.rcon('ObjectTemplate.refillAmmoSpeed %s' % self.ac_tpl_old[0])
            self.ac_tpl = 0
            self.log('arena crates: %s healSpeed back to %s' % (name, (self.crate_changed and '100') or self.ac_tpl_old[1]))

    def ac_count(self):
        return max(0, min(30, self.ci('ARENA_CRATES')))

    def ac_live(self):
        out = []
        for c in self.crates:
            if c.get('kind') == 'arena' and c['state'] == 'live':
                out.append(c)
        return out

    def ac_spots(self, n):
        """n arena points spread out: a random first one, then each time one of the 3 farthest from those
        taken (a point used in the last set counts half as far)."""
        cand = []
        for k in range(len(self.points)):
            if not self.point_bad(k):
                cand.append(k)
        if not cand:
            return []
        n = min(n, len(cand))
        fresh = []
        for k in cand:
            if k not in self.ac_prev:
                fresh.append(k)
        if not fresh:
            fresh = cand
        chosen = [fresh[self.rand.below(len(fresh))]]
        taken = {chosen[0]: 1}
        while len(chosen) < n:
            rows = []
            for k in cand:
                if k in taken:
                    continue
                pk = self.points[k]
                dmin = None
                for j in chosen:
                    pj = self.points[j]
                    d = ((pk[1] - pj[1]) ** 2 + (pk[3] - pj[3]) ** 2) ** 0.5
                    if dmin is None or d < dmin:
                        dmin = d
                if k in self.ac_prev:
                    dmin = dmin * 0.5
                rows.append((-dmin, k))
            if not rows:
                break
            rows.sort()
            top = rows[:3]
            k = top[self.rand.below(len(top))][1]
            chosen.append(k)
            taken[k] = 1
        return chosen

    def run_arena_crates(self, t):
        n = self.ac_count()
        if self.ac_checks:
            self.run_ac_checks(t)
        self.ac_find(t)
        if self.ended or self.arena is None or not self.points:
            return
        if n == 0:
            live = self.ac_live()
            if live or self.ac_tpl or self.ac_q:
                for c in live:
                    self.remove_crate(c, 'ARENA_CRATES 0', 1)
                self.crates = [c for c in self.crates if c['state'] != 'gone']
                self.crate_arena_tpl(0)
                self.ac_q = []
                self.log('arena crates: taken in (%d)' % len(live))
            return
        if not self.ac_tpl:
            self.crate_arena_tpl(1)
        if self.ac_next is None:
            self.ac_next = t + max(0, self.ci('ARENA_CRATE_START'))
            self.log('arena crates: the first %d in %d s (ARENA_CRATE_MODE %s)'
                     % (n, max(0, self.ci('ARENA_CRATE_START')), self.cs('ARENA_CRATE_MODE')))
        if t >= self.ac_next:
            self.ac_next = t + max(10, self.ci('ARENA_CRATE_EVERY'))
            self.ac_plan(n)
        made = 0
        while self.ac_q and made < 2:
            (slot, k) = self.ac_q.pop(0)
            made = made + 1
            try:
                self.ac_place(slot, k, t)
            except Exception:
                self.log('ERROR placing an arena crate: %s' % err_text())
        if made and not self.ac_q:
            st = self.ac_stat
            self.ac_sets = self.ac_sets + 1
            if self.ac_sets <= 3 or st['lost'] or st['unseen']:
                self.log('arena crates set %d: %d out (moved %d, made %d, reused %d, lost %d, not listed %d) at %s'
                         % (self.ac_sets, len(self.ac_live()), st['moved'], st['made'], st['reused'], st['lost'],
                            st['unseen'], ', '.join(st['at'])))

    def ac_plan(self, n):
        live = self.ac_live()
        rows = []
        for c in live:
            rows.append((c.get('slot', 99), c))
        rows.sort()
        for (slot, c) in rows[n:]:
            self.remove_crate(c, 'fewer crates', 1)
        self.crates = [c for c in self.crates if c['state'] != 'gone']
        ks = self.ac_spots(n)
        self.ac_prev = {}
        for k in ks:
            self.ac_prev[k] = 1
        self.ac_q = []
        for j in range(len(ks)):
            self.ac_q.append((j, ks[j]))
        self.ac_objs = None
        self.ac_stat = {'moved': 0, 'made': 0, 'reused': 0, 'lost': 0, 'unseen': 0, 'at': []}

    def ac_new(self):
        return self.cs('ARENA_CRATE_MODE').strip().lower() != 'move'

    def crate_spawner(self, name):
        """Our ObjectSpawner template that makes one crate when it is placed and never another (made once)."""
        if self.crate_sp:
            return self.crate_sp
        sp = 'fldm_crate_sp'
        lines = ['ObjectTemplate.create ObjectSpawner %s' % sp,
                 'ObjectTemplate.activeSafe ObjectSpawner %s' % sp,
                 'ObjectTemplate.isNotSaveable 1',
                 'ObjectTemplate.hasMobilePhysics 0',
                 'ObjectTemplate.setObjectTemplate 1 %s' % name,
                 'ObjectTemplate.setObjectTemplate 2 %s' % name,
                 'ObjectTemplate.minSpawnDelay 99999',
                 'ObjectTemplate.maxSpawnDelay 99999',
                 'ObjectTemplate.spawnDelayAtStart 0',
                 'ObjectTemplate.maxNrOfObjectSpawned 1']
        ans = []
        for ln in lines:
            a = self.rcon(ln)
            if a:
                ans.append('%s -> "%s"' % (ln, a))
        self.log('crate spawner template %s for %s: %s' % (sp, name, '; '.join(ans) or 'no answers'))
        self.crate_sp = sp
        return sp

    def crate_make(self, name, spot):
        """A crate at spot: (its object as the server lists it or None, id, the game's answers, the spawner's id).
        By the spawner way the game makes the crate a moment later: the object is looked for then (ac_find)."""
        if self.cs('ARENA_CRATE_WAY').strip().lower() != 'direct':
            sp = self.crate_spawner(name)
            a1 = self.rcon('Object.create %s' % sp)
            a2 = self.rcon('Object.absolutePosition %.2f/%.2f/%.2f' % (spot[0], spot[1], spot[2]))
            a3 = self.rcon('Object.layer 1')
            soid = ''
            w = a1.split()
            if w and w[0].lower().startswith('id'):
                soid = w[0]
            return (None, '', 'spawner "%s", position "%s", layer "%s"' % (a1, a2, a3), soid)
        n0 = len(self.crates_near(name, spot, 3.0))
        a1 = self.rcon('Object.create %s' % name)
        a2 = self.rcon('Object.absolutePosition %.2f/%.2f/%.2f' % (spot[0], spot[1], spot[2]))
        a3 = self.rcon('Object.layer 1')
        oid = ''
        w = a1.split()
        if w and w[0].lower().startswith('id'):
            oid = w[0]
        near = self.crates_near(name, spot, 3.0)
        obj = None
        if len(near) > n0:
            best = None
            for (o, q) in near:
                dd = dist3(q, spot)
                if best is None or dd < best:
                    best = dd
                    obj = o
        return (obj, oid, '"%s", position "%s", layer "%s"' % (a1, a2, a3), '')

    def ac_drop(self):
        return max(0.0, self.cf('ARENA_CRATE_DROP'))

    def ac_check_later(self, c, spot, label, t):
        for dt in (3.0, 15.0):
            self.ac_checks.append((t + dt, c, spot, label, dt))

    def ac_find(self, t):
        """Spawner crates: the crate the game made under our spawner (within 3 m across, between its point and the
        spawner) is ours - looked for every 0.5 s up to 8 s."""
        want = []
        for c in self.crates:
            if c.get('find') and c['state'] == 'live' and c['obj'] is None:
                want.append(c)
        if not want or t < getattr(self, 'ac_find_next', 0.0):
            return
        self.ac_find_next = t + 0.5
        name = self.cs('CRATE')
        self.calls = self.calls + 1
        try:
            objs = bf2.objectManager.getObjectsOfTemplate(name)
        except Exception:
            objs = []
        ours = []
        for c in self.crates:
            if c['obj'] is not None:
                ours.append(c['obj'])
        for c in want:
            (t0, high) = c['find']
            best = None
            for o in objs:
                taken = 0
                for x in ours:
                    if x is o:
                        taken = 1
                if taken:
                    continue
                self.calls = self.calls + 1
                try:
                    q = o.getPosition()
                    q = (float(q[0]), float(q[1]), float(q[2]))
                except Exception:
                    continue
                d = ((q[0] - high[0]) ** 2 + (q[2] - high[2]) ** 2) ** 0.5
                if d <= 3.0 and c['spot'][1] - 3.0 <= q[1] <= high[1] + 3.0:
                    if best is None or d < best[0]:
                        best = (d, o, q)
            if best is not None:
                c['obj'] = best[1]
                ours.append(best[1])
                del c['find']
                if self.ac_found_logged < 3:
                    self.ac_found_logged = self.ac_found_logged + 1
                    self.log('crate from the spawner seen %.1f s after it was placed, at %s' % (t - t0, fmt_pos(best[2])))
            elif t - t0 > 8.0:
                del c['find']
                self.ac_stat['unseen'] = self.ac_stat.get('unseen', 0) + 1
                if self.ac_found_logged < 6:
                    self.ac_found_logged = self.ac_found_logged + 1
                    self.log('NO crate from the spawner at %s in 8 s (the game made none, or it is not where it '
                             'should be)' % fmt_pos(high))

    def run_ac_checks(self, t):
        keep = []
        for row in self.ac_checks:
            (due, c, spot, label, dt) = row
            if t < due:
                keep.append(row)
                continue
            if c['obj'] is None:
                if c.get('find'):
                    self.log('%s: %d s after it was made - not found yet' % (label, int(dt)))
                else:
                    self.log('%s: %d s after it was made - not followed (the server did not list it)' % (label, int(dt)))
                continue
            self.calls = self.calls + 1
            try:
                q = c['obj'].getPosition()
                q = (float(q[0]), float(q[1]), float(q[2]))
            except Exception:
                self.log('%s: %d s after it was made - gone' % (label, int(dt)))
                continue
            d = ((q[0] - spot[0]) ** 2 + (q[2] - spot[2]) ** 2) ** 0.5
            self.log('%s: %d s after it was made at %s - %.1f m from its point, %.1f m over it'
                     % (label, int(dt), fmt_pos(q), d, q[1] - spot[1]))
        self.ac_checks = keep

    def ac_place(self, slot, k, t):
        pt = self.points[k]
        spot = (pt[1], pt[2] + 0.3, pt[3])
        high = (spot[0], spot[1] + self.ac_drop(), spot[2])
        name = self.cs('CRATE')
        st = self.ac_stat
        st['at'].append(pt[0])
        c = None
        for x in self.ac_live():
            if x.get('slot') == slot:
                c = x
        if c is not None and self.ac_new():
            self.remove_crate(c, 'a new one instead', 1)
            st['old'] = st.get('old', 0) + 1
        elif c is not None and c['obj'] is not None:
            if self.ac_objs is None:
                self.calls = self.calls + 1
                try:
                    self.ac_objs = bf2.objectManager.getObjectsOfTemplate(name)
                except Exception:
                    self.ac_objs = []
            there = 0
            for o in self.ac_objs:
                if o is c['obj']:
                    there = 1
            if there:
                try:
                    c['obj'].setPosition(high)
                    c['spot'] = spot
                    c['k'] = k
                    st['moved'] = st['moved'] + 1
                    return
                except Exception:
                    pass
            c['state'] = 'gone'
            st['lost'] = st['lost'] + 1
        elif c is not None:
            self.remove_crate(c, 'moved on', 1)
        self.crates = [x for x in self.crates if x['state'] != 'gone']
        if not self.ac_new():
            for pc in self.crates:
                if pc['state'] == 'parked' and pc['obj'] is not None:
                    try:
                        pc['obj'].setPosition(high)
                    except Exception:
                        pc['state'] = 'gone'
                        continue
                    pc['state'] = 'live'
                    pc['kind'] = 'arena'
                    pc['slot'] = slot
                    pc['k'] = k
                    pc['t'] = t
                    pc['until'] = 1e18
                    pc['ai'] = None
                    pc['spot'] = spot
                    st['reused'] = st['reused'] + 1
                    return
        (obj, oid, ans, soid) = self.crate_make(name, high)
        c = {'t': t, 'until': 1e18, 'oid': oid, 'ai': None, 'spot': spot, 'name': name, 'obj': obj,
             'state': 'live', 'kind': 'arena', 'slot': slot, 'k': k, 'sp_oid': soid}
        if soid or (obj is None and self.cs('ARENA_CRATE_WAY').strip().lower() != 'direct'):
            c['find'] = (t, high)
            c['spawner'] = 1
        elif obj is None:
            st['unseen'] = st['unseen'] + 1
        self.crates.append(c)
        st['made'] = st['made'] + 1
        if self.ac_logged < 2:
            self.ac_logged = self.ac_logged + 1
            seen = (obj is not None and 'yes') or 'NO'
            if c.get('find'):
                seen = 'looked for in a moment'
            self.log('arena crate %d at %s (%s, made %.0f m over it): %s; the server lists it there: %s'
                     % (slot + 1, pt[0], fmt_pos(spot), self.ac_drop(), ans, seen))
            self.ac_check_later(c, spot, 'arena crate %d (%s)' % (slot + 1, pt[0]), t)

    def compass(self, dx, dz):
        ax = abs(dx)
        az = abs(dz)
        ns = (dz >= 0 and 'north') or 'south'
        ew = (dx >= 0 and 'east') or 'west'
        if az >= ax * 2.414:
            return ns
        if ax >= az * 2.414:
            return ew
        return ns + '-' + ew

    def ac_where(self, p):
        """!dm crates where: the nearest arena crate - how far, which way, how high (for everybody)."""
        pos = self.pos_of(p)
        if pos is None:
            return
        best = None
        for c in self.ac_live():
            q = c['spot']
            if c['obj'] is not None:
                self.calls = self.calls + 1
                try:
                    r = c['obj'].getPosition()
                    q = (float(r[0]), float(r[1]), float(r[2]))
                except Exception:
                    pass
            d = ((q[0] - pos[0]) ** 2 + (q[2] - pos[2]) ** 2) ** 0.5
            if best is None or d < best[0]:
                best = (d, q, c)
        if best is None:
            wait = ''
            if self.ac_next is not None and self.ac_next > self.now():
                wait = ' - the next ones in %d s' % int(self.ac_next - self.now() + 0.5)
            self.say('[DM] %s: no ammo crates out right now%s.' % (self.name_of(p), wait))
            return
        (d, q, c) = best
        dy = q[1] - (pos[1] - 1.0)
        up = ''
        if dy > 3.0:
            up = ', %d m up' % int(dy + 0.5)
        elif dy < -3.0:
            up = ', %d m down' % int(-dy + 0.5)
        nm = ''
        if c.get('k') is not None and c['k'] < len(self.points):
            nm = ' (%s)' % self.points[c['k']][0]
        self.say('[DM] %s: the nearest ammo crate is %d m %s%s%s.' % (self.name_of(p), int(d + 0.5),
                                                                       self.compass(q[0] - pos[0], q[2] - pos[2]), up, nm))
        self.log('crates where for %s at %s: %d m to %s, crate at %s' % (self.name_of(p), fmt_pos(pos), int(d + 0.5), nm.strip(),
                                                                       fmt_pos(q)))

    def ac_here(self, p):
        """!dm crates here (test): one crate 3 m in front of the player, for 2 minutes - is it seen?"""
        s = self.soldier_of(p)
        pos = self.pos_of(p)
        if s is None or pos is None:
            return
        yaw = 0.0
        self.calls = self.calls + 1
        try:
            yaw = float(s.getRotation()[0])
        except Exception:
            pass
        spot = (pos[0] + sin_deg(yaw) * 3.0, pos[1] - 1.0 + 0.3, pos[2] + cos_deg(yaw) * 3.0)
        up = min(10.0, self.ac_drop())
        high = (spot[0], spot[1] + up, spot[2])
        name = self.cs('CRATE')
        t = self.now()
        (obj, oid, ans, soid) = self.crate_make(name, high)
        c = {'t': t, 'until': t + 120.0, 'oid': oid, 'ai': None, 'spot': spot, 'name': name, 'obj': obj,
             'state': 'live', 'kind': 'test', 'sp_oid': soid}
        if soid or (obj is None and self.cs('ARENA_CRATE_WAY').strip().lower() != 'direct'):
            c['find'] = (t, high)
            c['spawner'] = 1
        self.crates.append(c)
        self.log('crate here for %s at %s (made %.0f m over it, facing %.0f): create %s; the server lists it there: %s'
                 % (self.name_of(p), fmt_pos(spot), up, yaw, ans, (obj is not None and 'yes') or 'NO'))
        self.ac_check_later(c, spot, 'crate here for %s' % self.name_of(p), t)
        how = (obj is not None and 'the server has it') or 'the server has it: NO'
        if c.get('find'):
            how = 'made by a spawner'
        self.say('[DM] %s: a crate comes down 3 m in front of you, for 2 minutes (%s) - do you see it?'
                 % (self.name_of(p), how))

    def ac_text(self):
        n = self.ac_count()
        if n <= 0:
            return 'arena crates: none (ARENA_CRATES 0)'
        heal = 'no healing'
        if self.ci('ARENA_CRATE_HEAL') > 0:
            heal = 'healSpeed %d' % self.ci('ARENA_CRATE_HEAL')
        how = 'new ones'
        if not self.ac_new():
            how = 'moved'
        return 'arena crates: %d (%s, %d out now), %s every %d s' % (n, heal, len(self.ac_live()), how,
                                                                  max(10, self.ci('ARENA_CRATE_EVERY')))

    def ac_cmd(self, words, who):
        """crates [n | off | now]: how many ammo crates are spread over the arena (until the server restarts)."""
        if not words:
            return 'fldm: ' + self.ac_text()
        w = words[0].lower()
        if w == 'now':
            if not self.active:
                return 'fldm: deathmatch is not on this round'
            self.ac_next = self.now()
            return 'fldm: the arena crates move now'
        if w in ('off', 'none', 'no'):
            n = 0
        elif w == 'on':
            n = 10
        else:
            n = to_int(w, -1)
        if n < 0 or n > 30:
            return 'fldm: crates <0-30> | on | off | now (now: %s)' % self.ac_text()
        self.cfg['ARENA_CRATES'] = n
        self.ac_next = self.now()
        self.log('arena crates set by %s: ARENA_CRATES %d until the server restarts' % (who, n))
        if self.active:
            if n:
                self.say('[DM] %d ammo crates in the arena now - they move every %d s.'
                         % (n, max(10, self.ci('ARENA_CRATE_EVERY'))))
            else:
                self.say('[DM] No ammo crates in the arena now.')
        return 'fldm: ' + self.ac_text() + ' - until the server restarts (modmanager.con unchanged)'

    def onRouteTimer(self, data=None):
        """TP_STEP under 0.1 s: the sky route's steps get a timer of their own (the main one ticks every 0.1 s)."""
        if 1 != self.__state or not self.active or not self.tp_route:
            return
        try:
            self.run_routes(self.now())
        except Exception:
            self.log('ERROR in the route timer: %s' % err_text())

    # ------------------------------------------------------------------ on / off in the middle of a round
    def cmd_rcon(self, ctx, cmd):
        """FL Deathmatch: fldm on | off | status - on / off now, until the round ends"""
        who = 'rcon'
        try:
            who = 'rcon by %s' % clean(ctx.getName())
        except Exception:
            pass
        try:
            ans = self.switch(str(cmd or '').split(), who)
        except Exception:
            ans = 'fldm: ERROR %s' % err_text()
            self.log('ERROR in the rcon command: %s' % err_text())
        try:
            ctx.write(ans + '\n')
        except Exception:
            pass

    def switch(self, words, who):
        sub = 'status'
        if words:
            sub = words[0].lower()
        if sub == 'status':
            return self.status_text()
        if sub == 'on':
            mode = 'tdm'
            if len(words) > 1 and words[1].lower() != 'tdm':
                if words[1].lower() == 'ffa':
                    return 'fldm: free-for-all was taken out in 1.2.7 (fldm on = team deathmatch)'
                return USAGE
            if self.active and self.mode == mode:
                return 'fldm: %s is already on this round' % mode
            if not self.playing:
                return 'fldm: no round is being played now - try once it has started'
            if self.active:
                self.turn_off(who, 1)
            return self.turn_on(mode, who)
        if sub == 'off':
            return self.turn_off(who)
        if sub == 'band':
            return self.band_cmd(words[1:], who)
        if sub in ('hp', 'health'):
            return self.hp_cmd(words[1:], who)
        if sub in ('crates', 'crate', 'ammo'):
            return self.ac_cmd(words[1:], who)
        if sub == 'info':
            lines = self.info_lines()
            if len(words) > 1 and words[1].lower() == 'say':
                for x in lines:
                    self.say(x)
                return 'fldm: said in the chat: ' + ' / '.join(lines)
            return 'fldm: ' + ' / '.join(lines)
        if sub == 'hs':
            if len(words) > 1 and words[1].lower() in ('on', 'off'):
                on = (words[1].lower() == 'on') and 1 or 0
                self.cfg['HEADSHOTS'] = on
                self.log('headshots %s by %s (HEADSHOTS %d until the server restarts)' % ((on and 'ON' or 'off'), who, on))
                if not self.active:
                    return ('fldm: headshots only %s from when deathmatch is on (HEADSHOTS %d until the server '
                            'restarts)' % ((on and 'on' or 'off'), on))
                self.hs_want(on, who)
            return self.hs_status()
        if sub in WEAPON_WORDS:
            return self.weap_cmd(WEAPON_WORDS[sub], words[1:], who)
        if sub in TZ_WORDS:
            return self.tz_cmd(TZ_WORDS[sub], words[1:], who)
        if sub in ('weapons', 'damage'):
            return 'fldm: ' + self.hs_status() + '; ' + self.weap_status()
        return USAGE

    def info_lines(self):
        """!dm info / fldm info: which weapons kill now and how far from the enemy a spawn is dropped."""
        if not self.active:
            return ['[DM] Deathmatch is off this round (fldm %s).' % VERSION]
        names = {'nades': 'grenades', 'knife': 'knives', 'rockets': 'AT rockets', 'defib': 'paddles'}
        ons = ['guns']
        offs = []
        for g in WEAPON_GROUPS:
            nm = names.get(g[0], g[2])
            if self.weap_target[g[0]]:
                ons.append(nm)
            else:
                offs.append(nm)
        for g in TZ_GROUPS:
            if g[11]:
                continue
            if self.tz[g[0]]['target']:
                ons.append(g[3])
            else:
                offs.append(g[3])
        if self.hs_target:
            a = '[DM] Headshots only: of the guns only a bullet to the head kills'
            if not self.tz['snipers']['target']:
                a = a + ' (sniper rifles do no damage)'
            keep = []
            for (key, word) in (('knife', 'knives'), ('defib', 'paddles'), ('rockets', 'AT rockets')):
                if self.weap_target.get(key):
                    keep.append(word)
            if len(keep) > 1:
                a = a + '; %s and %s kill anywhere' % (', '.join(keep[:-1]), keep[-1])
            elif keep:
                a = a + '; %s kill anywhere' % keep[0]
            a = a + '.'
        else:
            a = '[DM] Weapons on: %s. Off: %s.' % (', '.join(ons), ', '.join(offs) or 'none')
        if self.hs_q:
            a = a + ' (being set now)'
        if self.tp_on():
            b = ('[DM] Spawn: you are dropped where the nearest enemy is %d-%d m away (never under %d m).'
                 % (self.ci('BAND_MIN'), self.ci('BAND_MAX'), self.ci('TP_ENEMY_MIN')))
        else:
            b = '[DM] Spawn: at your flags (the game\'s own spawn points, no drops).'
        out = [a, b + ' A frag gives %s.' % self.hp_text()]
        if self.ac_count() > 0:
            out.append('[DM] Ammo crates: %d in the arena (ammo only%s), they move every %d s - !dm crates where.'
                       % (self.ac_count(), (self.ci('ARENA_CRATE_HEAL') > 0 and ', some healing') or ', no healing',
                          max(10, self.ci('ARENA_CRATE_EVERY'))))
        return out

    def hp_text(self):
        hp = self.ci('FRAG_HP')
        if hp <= 0:
            return 'no health'
        if hp >= self.ci('HP_MAX'):
            return 'full health'
        return '+%d health' % hp

    def hp_cmd(self, words, who):
        """hp <n> | full | off: the health a frag gives (FRAG_HP), until the server restarts."""
        if not words:
            return 'fldm: a frag gives %s (FRAG_HP %d, HP_MAX %d)' % (self.hp_text(), self.ci('FRAG_HP'), self.ci('HP_MAX'))
        w = words[0].lower()
        mx = self.ci('HP_MAX')
        if w in ('full', 'max'):
            n = mx
        elif w in ('off', 'none', 'no'):
            n = 0
        else:
            n = to_int(w.lstrip('+'), -1)
        if n < 0 or n > mx:
            return 'fldm: hp <0-%d> | full | off (now: %s)' % (mx, self.hp_text())
        self.cfg['FRAG_HP'] = n
        self.log('frag health set by %s: FRAG_HP %d (%s) until the server restarts' % (who, n, self.hp_text()))
        if self.active:
            self.say('[DM] A frag now gives %s.' % self.hp_text())
        return 'fldm: a frag gives %s (FRAG_HP %d) - until the server restarts (modmanager.con unchanged)' % (
            self.hp_text(), n)

    def band_text(self):
        return ('spawn distance: nearest enemy %d-%d m where a point allows, never under %d m (%d m after %s s '
                'of waiting)' % (self.ci('BAND_MIN'), self.ci('BAND_MAX'), self.ci('TP_ENEMY_MIN'),
                                 self.ci('TP_ENEMY_LOW'), self.cs('TP_WAIT')))

    def band_cmd(self, words, who):
        """band min max [never under]: the drop distance now, until the server restarts (modmanager.con is
        not changed). A min under TP_ENEMY_MIN lowers that too."""
        if not words:
            return 'fldm: ' + self.band_text()
        nums = []
        for w in words[:3]:
            nums.append(to_int(w, -1))
        if len(nums) < 2 or nums[0] < 10 or nums[1] < nums[0] or nums[1] > 200:
            return 'fldm: band <min> <max> [never under] - metres, 10 <= min <= max <= 200 (now: %s)' % self.band_text()
        lo = nums[0]
        hi = nums[1]
        never = self.ci('TP_ENEMY_MIN')
        if len(nums) > 2:
            if nums[2] < 10 or nums[2] > lo:
                return 'fldm: "never under" must be 10 m to min (%d)' % lo
            never = nums[2]
        elif lo < never:
            never = lo
        self.cfg['BAND_MIN'] = lo
        self.cfg['BAND_MAX'] = hi
        self.cfg['TP_ENEMY_MIN'] = never
        if self.ci('TP_ENEMY_LOW') > never:
            self.cfg['TP_ENEMY_LOW'] = never
        self.log('band set by %s: %s' % (who, self.band_text()))
        self.say('[DM] Spawn distance now: the nearest enemy %d-%d m away (never under %d m)' % (lo, hi, never))
        return 'fldm: ' + self.band_text() + ' - until the server restarts (modmanager.con unchanged)'

    def status_text(self):
        now = 'off'
        if self.active:
            now = '%s (%s)' % (self.mode, self.mode_name())
            if self.forced:
                now = now + ', turned on in this round'
        nxt = self.cs('MODE').lower()
        if self.next_mode is not None:
            nxt = self.next_mode
        line = 'fldm %s: %s now on %s; the next round: %s (MODE %s)' % (VERSION, now, self.map or '?', nxt,
                                                                        self.cs('MODE'))
        if self.active and self.mode == 'tdm':
            line = line + '; %s %d - %s %d of %d' % (self.team_name(1), self.team_frags[1], self.team_name(2),
                                                    self.team_frags[2], self.limit())
        if self.hs_target or self.hs_on:
            line = line + '; ' + self.hs_status()
        if self.dmg_touched() or 0 in self.weap_wanted().values() or self.tz_touched():
            line = line + '; ' + self.weap_status()
        return line

    def turn_on(self, mode, who):
        tk = self.read_tickets()
        self.round_start(mode, who)
        self.saved_tk = tk
        if not self.active:
            return 'fldm: cannot be turned on here (no arena on %s)' % (self.map or '?')
        self.say('[DM] Deathmatch is ON (%s) until the end of this round - the new rules from your next spawn.'
                 % self.mode_name())
        return 'fldm: %s on until the end of this round' % mode

    def turn_off(self, who, quiet=0):
        if not self.active:
            return 'fldm: deathmatch is not on this round'
        self.log('deathmatch turned OFF in the middle of the round (%s)' % who)
        if not self.summarized:
            self.summary()
        try:
            self.clear_crates()
        except Exception:
            pass
        done = []
        if self.setup_at is None:
            n = 0
            for (cp, t, u) in self.flag_orig:
                try:
                    cp.cp_setParam('team', t)
                    cp.cp_setParam('flag', t)
                    n = n + 1
                except Exception:
                    self.log('flag: cannot set back (%s)' % err_text())
                    continue
                try:
                    cp.cp_setParam('takeOverChangePerSecond', 0.0)
                except Exception:
                    pass
                if u is not None:
                    try:
                        cp.cp_setParam('unableToChangeTeam', u)
                    except Exception:
                        pass
            done.append('%d flags back to their sides' % n)
            tk = []
            for t in (1, 2):
                rec = self.saved_tk.get(t)
                if not rec or rec[0] is None:
                    continue
                try:
                    bf2.gameLogic.setTickets(t, rec[0])
                    if rec[1] is not None:
                        bf2.gameLogic.setTicketLimit(t, 1, rec[1])
                    if rec[2] is not None:
                        bf2.gameLogic.setTicketChangePerSecond(t, rec[2])
                    tk.append('%s %s' % (self.team_name(t), rec[0]))
                except Exception:
                    self.log('tickets: cannot set back (%s)' % err_text())
            if tk:
                done.append('tickets back: ' + ', '.join(tk))
        self.restore_settings('deathmatch turned off')
        done.append(self.game_ticket_loss())
        self.active = 0
        self.mode = 'off'
        self.reset_round()
        self.log('deathmatch off until the round ends: %s' % '; '.join(done))
        if not quiet:
            self.say('[DM] Deathmatch is OFF until the end of this round - the flags can be taken again.')
        return 'fldm: off until the end of this round (%s)' % '; '.join(done)

    def game_ticket_loss(self):
        """The game mode's own ticket bleed worked out again for the flags as they are now."""
        gm = ''
        try:
            gm = str(host.ss_getParam('gameMode'))
        except Exception:
            gm = ''
        if not gm:
            return 'the game mode is not known - its ticket bleed comes back at the next flag change'
        for key in list(sys.modules.keys()):
            mod = sys.modules.get(key)
            if mod is None or key.split('.')[-1] != gm or not hasattr(mod, 'updateTicketLoss'):
                continue
            try:
                mod.updateTicketLoss()
                return '%s.updateTicketLoss() done' % gm
            except Exception:
                return '%s.updateTicketLoss() failed (%s)' % (gm, err_text())
        return '%s has no updateTicketLoss - its ticket bleed comes back at the next flag change' % gm

    # ------------------------------------------------------------------ chat commands
    def onChatMessage(self, playerId, text, channel, flags):
        if 1 != self.__state:
            return
        try:
            self.chat(playerId, text)
        except Exception:
            self.log('ERROR in chat: %s' % err_text())

    def chat(self, playerId, text):
        text = str(text)
        k = text.find('!dm')
        if k < 0:
            return
        words = text[k:].split()
        if not words or words[0] != '!dm':
            return
        if playerId is None or playerId < 0:
            return
        p = self.by_index(playerId)
        cmd = ''
        if len(words) > 1:
            cmd = words[1].lower()
        if cmd == '' or cmd == 'score':
            if not self.ci('PUBLIC_SCORE') and not self.ci('TEST_COMMANDS'):
                return
            if not self.active:
                self.say('[DM] Deathmatch is off this round (fldm %s)' % VERSION)
                return
            line = self.standings_line(0)
            if p is not None and p.index in self.frags:
                line = line + ' | %s: %d (%s)' % (self.name_of(p), self.frags[p.index],
                                                 ordinal(self.place_of(p.index)))
            self.say(line)
            return
        if cmd in ('crates', 'crate', 'ammo') and len(words) > 2 and words[2].lower() in ('where', 'here'):
            sub2 = words[2].lower()
            if sub2 == 'where' and (self.ci('PUBLIC_SCORE') or self.ci('TEST_COMMANDS')):
                if self.active and p is not None:
                    t = self.now()
                    last = getattr(self, 'where_said', -1000.0)
                    if t - last >= 3.0 or t < last:
                        self.where_said = t
                        self.ac_where(p)
                return
            if sub2 == 'here' and self.ci('TEST_COMMANDS'):
                if self.active and p is not None:
                    self.log('command from %s: %s' % (self.name_of(p), ' '.join(words)))
                    self.ac_here(p)
                return
        if cmd == 'info':
            if not self.ci('PUBLIC_SCORE') and not self.ci('TEST_COMMANDS'):
                return
            t = self.now()
            last = getattr(self, 'info_said', -1000.0)
            if t - last < 5.0 and t >= last:
                return
            self.info_said = t
            for x in self.info_lines():
                self.say(x)
            return
        if not self.ci('TEST_COMMANDS'):
            # said once a minute, so that a command typed on a server without them is not silently lost
            t = self.now()
            if t - getattr(self, 'test_off_said', -1000.0) > 60.0 or t < getattr(self, 'test_off_said', 0.0):
                self.test_off_said = t
                self.log('command from %s ignored (TEST_COMMANDS 0): %s' % (self.name_of(p), ' '.join(words)))
                self.say('[DM] Chat commands are off on this server (mm_fldm.TEST_COMMANDS 1); admins: rcon "fldm ..."')
            return
        self.log('command from %s: %s' % (self.name_of(p), ' '.join(words)))
        if cmd == 'help':
            self.say('[DM] !dm, !dm info, !dm on | off | status (now, this round), mode tdm|off (next round), '
                     'hs | nades | knife | rockets | defib | snipers | stationary | vehmg on|off, weapons, '
                     'band <min> <max>, hp <n>, crates <n>|now, '
                     'here [us|mec|any], where, points, tp <n>, limit <n>, end, drop, scan')
            return
        if cmd in ('on', 'off', 'status', 'hs', 'band', 'weapons', 'damage', 'hp', 'health', 'crates', 'crate',
                   'ammo') or cmd in WEAPON_WORDS or \
                cmd in TZ_WORDS:
            ans = self.switch(words[1:], 'chat by %s' % self.name_of(p))
            self.say('[DM] ' + ans.replace('fldm: ', ''))
            return
        if cmd == 'mode' and len(words) > 2 and words[2].lower() in ('tdm', 'off'):
            self.next_mode = words[2].lower()
            self.say('[DM] mode %s from the next round' % self.next_mode)
            return
        if cmd == 'limit' and len(words) > 2:
            n = to_int(words[2], 0)
            if n > 0:
                self.limit_override = n
                self.tickets_dirty = 1
                self.say('[DM] frag limit %d (until the server restarts)' % n)
            return
        if cmd == 'end':
            if self.active:
                tm = 1
                if self.team_frags[2] > self.team_frags[1]:
                    tm = 2
                self.start_end(tm, '[DM] Round ended by a test command')
            return
        if cmd == 'points':
            self.say('[DM] %d arena points on %s: %s' % (len(self.points), self.map,
                                                        ' '.join(['%d=%s(%s)' % (j, self.points[j][0],
                                                                                 self.side_word(self.points[j][5]))
                                                                  for j in range(len(self.points))])))
            return
        if p is None:
            return
        if cmd == 'tp' and len(words) > 2:
            j = to_int(words[2], -1)
            if 0 <= j < len(self.points) and self.alive(p):
                self.teleport(p, j, 'command')
                self.say('[DM] %s -> point %d %s' % (self.name_of(p), j, self.points[j][0]))
            return
        pos = self.pos_of(p)
        if pos is None:
            self.say('[DM] cannot read your place')
            return
        if cmd == 'where':
            a = 'no arena'
            if self.arena is not None:
                a = 'inside the arena'
                if not self.in_arena(pos):
                    a = 'OUTSIDE the arena'
                else:
                    e = min(pos[0] - self.arena[0], self.arena[2] - pos[0], pos[2] - self.arena[1],
                            self.arena[3] - pos[2])
                    a = a + ', %.0f m from its edge' % e
            self.say('[DM] %s at %.1f %.1f %.1f: %s' % (self.name_of(p), pos[0], pos[1], pos[2], a))
            return
        if cmd == 'here':
            yaw = 0.0
            s = self.soldier_of(p)
            try:
                yaw = float(s.getRotation()[0])
            except Exception:
                yaw = 0.0
            side = 0
            if self.mode == 'tdm':
                side = self.team_of(p)
            if len(words) > 2:
                side = self.side_of(words[2])
            ground = pos[1] - 1.0
            n = len(self.points)
            self.points.append(('here_%d' % n, pos[0], ground, pos[2], yaw, side))
            self.say('[DM] point %d added: %.2f %.2f %.2f %.0f %s' % (n, pos[0], ground, pos[2], yaw,
                                                                     self.side_word(side)))
            extra = [x for x in self.points if x[0].startswith('here_') or x[0].startswith('extra_')]
            self.log('POINTS line for modmanager.con: mm_fldm.POINTS "%s: %s"'
                     % (self.map, ', '.join(['%.2f %.2f %.2f %.0f %s' % (x[1], x[2], x[3], x[4], self.side_word(x[5]))
                                             for x in extra])))
            return
        if cmd == 'drop':
            mode = self.drop_mode()
            if len(words) > 2 and words[2].lower() in ('bags', 'crate', 'spawner'):
                mode = words[2].lower()
            if mode == 'off':
                mode = 'bags'
            team = self.team_of(p)
            r = self.make_drop((pos[0] + 2.0, pos[1], pos[2]), team, self.name_of(p) + ' (test)', mode, 1)
            self.say('[DM] drop test (%s) 2 m east of %s: %d made, the server lists %d new there, %d elsewhere'
                     % (mode, self.name_of(p), r[0], r[1], r[2]))
            return
        if cmd == 'scan':
            seen = {}
            lists = []
            for typ in (PROJ_TYPE, SUPPLY_TYPE):
                try:
                    lists.append(bf2.objectManager.getObjectsOfType(typ))
                except Exception:
                    pass
            for nm in (self.cs('MED_BAG'), self.cs('AMMO_BAG'), self.cs('CRATE')):
                lists.append(list(self.objects_of(nm).values()))
            done = {}
            for objs in lists:
                for o in objs:
                    if id(o) in done:
                        continue
                    done[id(o)] = 1
                    try:
                        q = o.getPosition()
                        q = (float(q[0]), float(q[1]), float(q[2]))
                    except Exception:
                        continue
                    if dist3(q, pos) <= 10.0:
                        nm = self.tpl(o)
                        seen[nm] = seen.get(nm, 0) + 1
            names = list(seen.keys())
            names.sort()
            self.say('[DM] within 10 m: ' + (', '.join(['%s x%d' % (nm, seen[nm]) for nm in names]) or 'nothing'))
            return


def mm_load(modManager):
    return FLDeathmatch(modManager)
