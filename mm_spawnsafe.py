# vim: ts=4 sw=4 noexpandtab
"""SpawnSafe - protection right after a spawn at a flag (=FL= Strike at Karkand 64).

A soldier who spawns on foot at one of his side's flag spawn points cannot lose
health for WINDOW seconds: the script puts his health back every server frame.
Nobody is warned or kicked for shooting him. The protection ends at once when:
  - the WINDOW (2 s) is over;
  - he moves MOVE (0.5 m) from where he appeared, or jumps;
  - he gets into a vehicle or onto a gun;
  - he kills somebody himself;
  - the enemy starts taking that flag (more enemies than defenders in its zone).
Not protected: the main bases (Gas Station, Factory), squad-leader spawns,
spawns straight into a vehicle.

A hit that takes all his health at once (knife, sniper, rocket, a tank or APC
gun) is not stopped by putting health back. If an enemy kills him that way
while he is protected, the killer is punished:
  - on foot: killed (health 0; put down again if a medic revives him within
    KEEP_DOWN s);
  - in a vehicle or on a gun: the first time a warning in the chat
    (VEH_WARNINGS 1 a round); the next time the vehicle / gun is set to
    VEH_HP_LEFT health, so it burns out with its crew; if he gets out within
    VEH_GRACE s he is killed on foot.
Not punished: claymores, C4, AT mines, artillery (SKIP), teamkills, suicides.

Standalone ModManager module (it does not need mm_flbus). It never asks the
game for every PlayerControlObject or for projectiles.

===== Install =====
  admin/modules/mm_spawnsafe.py
  modmanager.con:  modmanager.loadModule "mm_spawnsafe"
Switch off the AutoAdmin spawnkill rule (warnings + kick): never both.

===== Config (modmanager.con, mm_spawnsafe.<NAME>) =====
See configDefaults below and README-INSTALL.txt.

Log: spawnsafe.log (next to the other module logs).
"""

import host
import bf2
import math
import time
import sys

try:
	import mm_utils
except Exception:
	mm_utils = None

__version__ = 1.01

__required_modules__ = {
	'modmanager': 1.0
}

__supports_reload__ = True

__supported_games__ = {
	'bf2': True
}

__description__ = "SpawnSafe v%s - protection right after a flag spawn" % __version__

VERSION_TEXT = "1.0.1"

configDefaults = {
	'ENABLED': 1,
	'WINDOW': 2.0,            # seconds of protection after a flag spawn
	'MOVE': 0.5,              # metres from where he appeared (across) - ends it
	'JUMP_UP': 0.35,          # metres above his lowest point since the spawn - ends it
	'CAPTURE_OFF': 1,         # 1: no protection while the enemy is taking the flag
	'CAPTURE_EVERY': 0.1,     # seconds between looks at a protected flag's zone
	'SPAWN_MATCH': 2.5,       # metres (across) from a spawn point to count as spawned there
	'SPAWN_UP': 3.0,          # he may appear up to this much over the point (+1.25 points)
	'SPAWN_DOWN': 1.5,        # ... or this much under it
	'SL_NEAR': 4.0,           # spawned this close to his squad leader: a squad-leader spawn
	'MAIN_BASES': 'gasstation factory',
	'OVER_HP': 0,             # test: >0 sets health to this for the window (one-hit test)
	'PUNISH': 1,
	'SKIP': 'c4 claymore mine usart ars_ artillery',
	'SAME_ATTACK': 2.0,       # more kills by the same player within this: punished once
	'VEH_HP_LEFT': 1.0,       # health a punished vehicle / gun is set to
	'VEH_WARNINGS': 1,        # from a vehicle / gun: warnings a round before it is destroyed
	'VEH_GRACE': 15.0,        # a punished crew: killed on getting out within this; kills not counted
	'KEEP_DOWN': 20.0,        # a punished soldier revived within this is put down again
	'CHECK_AFTER': 12.0,      # look at a punished player again after this (log)
	'CHAT_GUARD': 1,          # say when the protection took a hit
	'MSG_GUARD': '[SpawnSafe] {victim} is spawn-protected at {flag}: no damage for {window} s after a spawn',
	'MSG_KILL': '[SpawnSafe] {killer} killed for killing {victim} right after his spawn at {flag}',
	'MSG_VEH': '[SpawnSafe] {killer}\'s {vehicle} destroyed for killing {victim} right after his spawn at {flag}',
	'MSG_VEH_WARN': '[SpawnSafe] {killer}: warning - you killed {victim} from your {vehicle} right after his spawn at {flag}. Next time your {vehicle} is destroyed',
	'MSG_LATER': '[SpawnSafe] {killer} dies when he leaves his {vehicle}: he killed {victim} right after his spawn at {flag}',
	'CHAT_MAX': 180,
	'MAP': 'karkand',
	'TEST_CHAT': 0,           # test: every start / end of a protection in the chat
	'TEST_COMMANDS': 0,       # test: !ss commands
	'TEST_TK': 0,             # test: a teammate's kill counts as an enemy's
	'ADMINS': '',             # who may use !ss: '' nobody, '*' anybody, or names
	'LOG_FILE': 'spawnsafe.log',
	'LOG_CONSOLE': 0
}

# ---------------------------------------------------------------------------
# Strike at Karkand, gpm_cq 64 (GamePlayObjects.con of the server's level).
# Flags: name, x, h, z, radius.  Spawn points: name, flag, x, h, z.
# ---------------------------------------------------------------------------
KARKAND64_FLAGS = [
	('gasstation', 'Gas Station', -161.03, 161.29, -262.83, 10.0),
	('hotel', 'Hotel', -194.41, 158.22, 11.42, 5.0),
	('square', 'Square', -220.07, 155.80, 98.08, 10.0),
	('trainaccident', 'Train Accident', -122.36, 149.89, 256.64, 6.0),
	('gatehouse', 'Gatehouse', 13.95, 155.99, 288.94, 10.0),
	('cementfactory', 'Cement Factory', 29.44, 149.99, 164.43, 9.0),
	('warehouse', 'Warehouse', 103.95, 152.70, 231.06, 5.0),
	('factory', 'Factory', 183.00, 152.69, 166.00, 10.0),
	('suburb', 'Suburb', -323.72, 168.39, 220.17, 10.0),
]

KARKAND64_POINTS = [
	('gasstation_1', 'gasstation', -160.96, 161.30, -266.02),
	('gasstation_2', 'gasstation', -179.00, 161.30, -316.00),
	('gasstation_3', 'gasstation', -121.76, 161.30, -282.87),
	('gasstation_4', 'gasstation', -160.16, 161.30, -319.51),
	('hotel_1', 'hotel', -189.80, 155.90, 26.38),
	('hotel_2', 'hotel', -222.87, 155.90, -3.19),
	('hotel_3', 'hotel', -189.34, 155.90, 0.62),
	('hotel_4', 'hotel', -189.35, 155.90, 0.59),
	('square_1', 'square', -244.96, 155.90, 123.39),
	('square_2', 'square', -206.03, 155.90, 106.99),
	('square_3', 'square', -251.06, 155.90, 82.85),
	('square_4', 'square', -247.86, 155.90, 104.55),
	('trainaccident_2', 'trainaccident', -121.99, 149.90, 285.92),
	('trainaccident_3', 'trainaccident', -146.07, 149.80, 309.50),
	('trainaccident_4', 'trainaccident', -161.57, 149.90, 240.57),
	('trainaccident_5', 'trainaccident', -119.56, 149.90, 236.87),
	('gatehouse_1', 'gatehouse', -9.49, 156.00, 288.47),
	('gatehouse_3', 'gatehouse', 49.95, 156.00, 283.35),
	('gatehouse_4', 'gatehouse', -6.01, 150.00, 241.04),
	('gatehouse_5', 'gatehouse', -16.66, 150.00, 250.75),
	('cementfactory_2', 'cementfactory', 12.32, 150.00, 184.58),
	('cementfactory_4', 'cementfactory', -16.05, 150.00, 187.96),
	('cementfactory_5', 'cementfactory', 10.15, 150.00, 158.87),
	('factory_1', 'factory', 213.45, 152.70, 194.76),
	('factory_2', 'factory', 216.81, 152.70, 148.82),
	('factory_3', 'factory', 163.97, 152.70, 128.31),
	('factory_4', 'factory', 166.74, 152.70, 178.32),
	('factory_5', 'factory', 186.74, 152.70, 130.64),
	('warehouse_1', 'warehouse', 105.55, 152.80, 215.37),
	('warehouse_2', 'warehouse', 126.53, 152.70, 274.86),
	('warehouse_3', 'warehouse', 121.03, 153.86, 239.18),
	('warehouse_4', 'warehouse', 93.39, 160.87, 246.65),
	('warehouse_5', 'warehouse', 91.75, 159.20, 211.49),
	('gasstation_6', 'gasstation', -171.87, 162.50, -114.16),
	('gasstation_7', 'gasstation', -160.07, 162.50, -131.85),
	('gasstation_8', 'gasstation', -150.16, 162.50, -113.54),
	('gasstation_9', 'gasstation', -236.02, 163.40, -142.86),
	('gasstation_10', 'gasstation', -253.53, 163.40, -139.59),
	('gasstation_11', 'gasstation', -252.87, 163.40, -159.38),
	('suburb_1', 'suburb', -315.93, 168.42, 236.87),
	('suburb_2', 'suburb', -355.01, 173.70, 171.52),
	('suburb_3', 'suburb', -283.31, 167.30, 221.08),
	('suburb_5', 'suburb', -339.71, 168.70, 223.19),
	('gasstation_11_0', 'gasstation', -231.69, 163.41, -171.93),
	('gasstation_12', 'gasstation', -135.40, 163.77, -132.96),
	('factory_6', 'factory', 226.73, 152.70, 160.74),
	('gatehouse_5_0', 'gatehouse', 25.62, 156.00, 314.60),
	('hotel_5', 'hotel', -222.77, 155.90, 14.73),
]

CP_TYPE = 'dice.hfe.world.ObjectTemplate.ControlPoint'
LAYOUT_MATCH = 3.0      # metres: a game flag this close to a table flag is that flag
LAYOUT_NEED = 7         # table flags that must be found to take the layout
DRIVEABLE = ('jep_', 'apc_', 'tnk_', 'aav_', 'ahe_', 'the_', 'air_', 'boat')
CHAT_PREFIXES = ('HUD_TEXT_CHAT_TEAM', 'HUD_TEXT_CHAT_SQUAD', 'HUD_TEXT_CHAT_COMMANDER',
	'HUD_CHAT_DEADPREFIX', '*\xa71DEAD\xa70*')


def _now():
	try:
		return host.timer_getWallTime()
	except Exception:
		return time.time()


def _f(v, d):
	try:
		return float(v)
	except Exception:
		return d


def _i(v, d):
	try:
		return int(float(v))
	except Exception:
		return d


def _s(v, d):
	if v is None:
		return d
	try:
		v = str(v)
	except Exception:
		return d
	if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
		v = v[1:-1]
	return v


def _dist2(a, b):
	dx = a[0] - b[0]
	dz = a[2] - b[2]
	return math.sqrt(dx * dx + dz * dz)


def _err():
	e = sys.exc_info()[1]
	try:
		return '%s: %s' % (e.__class__.__name__, e)
	except Exception:
		return 'error'


def _fmt(tpl, d):
	out = tpl
	for k in d.keys():
		out = out.replace('{' + k + '}', str(d[k]))
	return out


def _pretty_vehicle(name):
	n = str(name).lower()
	table = [
		('usapc_lav25', 'LAV-25'), ('apc_btr90', 'BTR-90'), ('ustnk_m1a2', 'M1A2'),
		('rutnk_t90', 'T-90'), ('usaav_m6', 'M6 Bradley'), ('ruaav_tunguska', 'Tunguska'),
		('usjep_hmmwv', 'Humvee'), ('rujep_vodnik', 'Vodnik'), ('jep_paratrooper', 'jeep'),
		('mec_bipod', 'machine gun'), ('ustow', 'TOW'), ('hj8', 'HJ-8'), ('chhj8', 'HJ-8'),
		('ars_d30', 'artillery'), ('usart', 'artillery'), ('ahe_', 'helicopter'),
		('air_', 'jet'), ('boat', 'boat'), ('tnk_', 'tank'), ('apc_', 'APC'), ('jep_', 'jeep'),
		('aav_', 'AA vehicle'),
	]
	for k, v in table:
		if n.find(k) >= 0:
			return v
	return n


class SpawnSafe(object):

	def __init__(self, modManager):
		self.mm = modManager
		self.__state = 0
		self.c = {}
		self.logf = None
		self.reset_round()
		self.calls = 0
		self.veh_way = {}       # template -> 'own' | 'im_func' | 'class' | 'none'
		self.last_status = None

	# ------------------------------------------------------------------ config
	def load_config(self):
		cfg = {}
		try:
			cfg = self.mm.getModuleConfig(configDefaults)
		except Exception:
			cfg = {}
		c = {}
		for k in configDefaults.keys():
			d = configDefaults[k]
			v = cfg.get(k, d)
			if isinstance(d, float):
				c[k] = _f(v, d)
			elif isinstance(d, int):
				c[k] = _i(v, d)
			else:
				c[k] = _s(v, d)
		self.c = c
		self.skip = []
		for w in c['SKIP'].replace(',', ' ').split():
			self.skip.append(w.lower())
		self.main_bases = {}
		for w in c['MAIN_BASES'].replace(',', ' ').split():
			self.main_bases[w.lower()] = 1
		self.admins = []
		for w in c['ADMINS'].replace(',', ' ').split():
			self.admins.append(w.lower())

	# ------------------------------------------------------------------ log
	def log(self, msg):
		t = self.rt()
		line = '%s [%7.2f] %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), t, msg)
		try:
			if self.logf is None:
				self.logf = open(self.c.get('LOG_FILE', 'spawnsafe.log'), 'a')
			self.logf.write(line + '\n')
			self.logf.flush()
		except Exception:
			pass
		if self.c.get('LOG_CONSOLE', 0):
			try:
				self.mm.info('SpawnSafe: ' + msg)
			except Exception:
				pass

	def rt(self):
		if self.round_t0 is None:
			return 0.0
		return _now() - self.round_t0

	def say(self, msg):
		msg = str(msg).replace('"', "'")
		mx = self.c.get('CHAT_MAX', 180)
		if mx < 40:
			mx = 40
		parts = []
		while len(msg) > mx:
			cut = msg.rfind(' ', 0, mx)
			if cut < 20:
				cut = mx
			parts.append(msg[:cut])
			msg = msg[cut:].lstrip()
		if msg:
			parts.append(msg)
		for p in parts:
			try:
				host.rcon_invoke('game.sayAll "%s"' % p)
			except Exception:
				self.log('chat failed: ' + _err())

	def test_say(self, msg):
		if self.c.get('TEST_CHAT', 0):
			self.say('[SpawnSafe test] ' + msg)

	# ------------------------------------------------------------------ rounds
	def reset_round(self):
		self.round_t0 = None
		self.active = 0
		self.flags = {}         # key -> dict(name, label, pos, radius, cp, team_bad)
		self.points = []        # (name, flagkey, (x, h, z))
		self.prot = {}          # player index -> protection record
		self.doomed = {}        # player index -> dict(until, ...)
		self.keep_down = {}     # player index -> until
		self.last_punish = {}   # player index -> time
		self.veh_warned = {}    # player index -> vehicle warnings this round
		self.later = []         # (time, fn, args)
		self.pending = []       # spawns whose place is not known yet
		self.st = {'spawns': 0, 'flag': 0, 'base': 0, 'sl': 0, 'other': 0, 'vehicle': 0,
			'taken': 0, 'protected': 0, 'hits': 0, 'hp': 0.0, 'saved_kills': 0,
			'punished': 0, 'warned': 0, 'not_punished': 0, 'ends': {}}
		self.calls = 0

	def round_start(self):
		self.reset_round()
		self.round_t0 = _now()
		if not self.c.get('ENABLED', 1):
			self.log('round start: ENABLED 0 - idle')
			return
		mapname = ''
		try:
			mapname = str(bf2.gameLogic.getMapName())
			self.calls += 1
		except Exception:
			mapname = '?'
		if mapname.lower().find(self.c.get('MAP', 'karkand').lower()) < 0:
			self.log('round on %s: not %s - idle' % (mapname, self.c.get('MAP')))
			return
		cps = []
		try:
			cps = bf2.objectManager.getObjectsOfType(CP_TYPE)
			self.calls += 1
		except Exception:
			self.log('could not list the flags: ' + _err())
			cps = []
		found = 0
		used = {}
		for key, label, x, h, z, radius in KARKAND64_FLAGS:
			best = None
			bestd = LAYOUT_MATCH
			for cp in cps:
				try:
					p = cp.getPosition()
					self.calls += 1
				except Exception:
					continue
				d = _dist2(p, (x, h, z))
				if d <= bestd and not used.get(id(cp)):
					best = cp
					bestd = d
			if best is not None:
				used[id(best)] = 1
				found += 1
			self.flags[key] = {'key': key, 'label': label, 'pos': (x, h, z), 'radius': radius,
				'cp': best, 'look': -1.0, 'taking': 0, 'warned': 0}
		if found < LAYOUT_NEED:
			self.log('round on %s: %d game flags, %d of %d Karkand 64 flags found - not the 64 layout, idle'
				% (mapname, len(cps), found, len(KARKAND64_FLAGS)))
			self.flags = {}
			return
		for name, fk, x, h, z in KARKAND64_POINTS:
			if self.main_bases.get(fk):
				continue
			if self.flags.get(fk) is None or self.flags[fk]['cp'] is None:
				continue
			self.points.append((name, fk, (x, h, z)))
		self.active = 1
		self.log('round on %s: layout gpm_cq 64 (%d game flags, %d found), %d protected spawn points at %d flags; '
			'WINDOW %.1f s, MOVE %.2f m, CAPTURE_OFF %d, PUNISH %d, OVER_HP %d'
			% (mapname, len(cps), found, len(self.points), len(self.flag_keys()),
			self.c['WINDOW'], self.c['MOVE'], self.c['CAPTURE_OFF'], self.c['PUNISH'], self.c['OVER_HP']))

	def flag_keys(self):
		ks = {}
		for name, fk, pos in self.points:
			ks[fk] = 1
		return ks.keys()

	def round_end(self):
		if self.round_t0 is None:
			return
		st = self.st
		ends = []
		for k in list(st['ends'].keys()):
			ends.append('%s %d' % (k, st['ends'][k]))
		dur = self.rt()
		rate = 0.0
		if dur > 1.0:
			rate = self.calls / dur
		self.log('round end: spawns %d (flag points %d, main base %d, squad leader %d, other %d, vehicle %d); '
			'flag being taken %d; protected %d; hits taken %d (%.0f health given back); kills of protected %d; '
			'warned (vehicles) %d, punished %d, not punished %d; ends: %s'
			% (st['spawns'], st['flag'], st['base'], st['sl'], st['other'], st['vehicle'], st['taken'],
			st['protected'], st['hits'], st['hp'], st['saved_kills'], st['warned'], st['punished'], st['not_punished'],
			', '.join(ends) or '-'))
		self.log('asked of the game this round: ~%d times (%.1f a second)' % (self.calls, rate))
		# put back over-max health of anyone still protected
		for idx in list(self.prot.keys()):
			self.end_prot(idx, 'round end')
		self.round_t0 = None
		self.active = 0

	def onGameStatusChanged(self, status):
		if 1 != self.__state:
			return
		last = self.last_status
		self.last_status = status
		try:
			if status == bf2.GameStatus.Playing:
				if last == bf2.GameStatus.Paused and self.round_t0 is not None:
					self.log('game unpaused - round goes on')
				else:
					self.round_start()
			elif status == bf2.GameStatus.EndGame:
				self.round_end()
		except Exception:
			self.log('game status %s: %s' % (status, _err()))

	# ------------------------------------------------------------------ helpers
	def name_of(self, p):
		try:
			return str(p.getName())
		except Exception:
			return '?'

	def alive(self, p):
		try:
			self.calls += 2
			return p.isAlive() and not p.isManDown()
		except Exception:
			return 0

	def root_of(self, p):
		"""Return (root object, soldier) for a player; root is the soldier on foot."""
		soldier = None
		v = None
		try:
			soldier = p.getDefaultVehicle()
			v = p.getVehicle()
			self.calls += 2
		except Exception:
			return (None, soldier)
		if v is None:
			return (soldier, soldier)
		try:
			r = bf2.objectManager.getRootParent(v)
			self.calls += 1
		except Exception:
			r = v
		return (r, soldier)

	def is_soldier(self, obj, soldier):
		if obj is None:
			return 1
		if soldier is None:
			return 0
		if obj == soldier:
			return 1
		# the same game object handed over as another Python object
		try:
			if obj.templateName == soldier.templateName and obj.getParent() is None:
				return 1
		except Exception:
			pass
		return 0

	def template(self, obj):
		try:
			return str(obj.templateName)
		except Exception:
			return '?'

	def flag_taking(self, f, team):
		"""1 if more enemies than defenders (team) are in the flag's zone, as the game counts it."""
		cp = f['cp']
		if cp is None:
			return 0
		objs = None
		tid = getattr(cp, 'triggerId', None)
		if tid is not None:
			try:
				objs = bf2.triggerManager.getObjects(tid)
				self.calls += 1
			except Exception:
				objs = None
		own = 0
		enemy = 0
		if objs is not None:
			for o in objs:
				if not o:
					continue
				try:
					if o.getParent():
						continue
					occ = o.getOccupyingPlayers()
					self.calls += 2
				except Exception:
					continue
				if not occ:
					continue
				p = occ[0]
				if not self.alive(p):
					continue
				try:
					t = p.getTeam()
					self.calls += 1
				except Exception:
					continue
				if t == team:
					own += 1
				elif t > 0:
					enemy += 1
		else:
			if not f.get('warned'):
				f['warned'] = 1
				self.log('%s: no trigger of the game mode - zone counted by distance (radius %.0f m)'
					% (f['label'], f['radius']))
			for p in self.players():
				if not self.alive(p):
					continue
				r, s = self.root_of(p)
				try:
					pos = r.getPosition()
					t = p.getTeam()
					self.calls += 2
				except Exception:
					continue
				if math.sqrt((pos[0] - f['pos'][0]) ** 2 + (pos[1] - f['pos'][1]) ** 2 +
					(pos[2] - f['pos'][2]) ** 2) > f['radius']:
					continue
				if t == team:
					own += 1
				elif t > 0:
					enemy += 1
		return enemy > own

	def players(self):
		try:
			self.calls += 1
			return bf2.playerManager.getPlayers()
		except Exception:
			return []

	# ------------------------------------------------------------------ spawns
	def onPlayerSpawn(self, player, soldier):
		if 1 != self.__state or not self.active:
			return
		try:
			self.st['spawns'] += 1
			self.forget(player, 0)
			# a new life: earlier punishments are over
			idx = player.index
			if idx in self.keep_down:
				del self.keep_down[idx]
			if idx in self.doomed:
				del self.doomed[idx]
			self.pending.append((player, soldier, _now(), 0))
			self.look_pending()
		except Exception:
			self.log('PlayerSpawn: ' + _err())

	def look_pending(self):
		keep = []
		now = _now()
		for player, soldier, t0, tries in self.pending:
			done = self.place_spawn(player, soldier, t0, tries)
			if not done and now - t0 < 0.3:
				keep.append((player, soldier, t0, tries + 1))
			elif not done:
				self.st['other'] += 1
				self.log('%s spawned, place never read - not protected' % self.name_of(player))
		self.pending = keep

	def place_spawn(self, player, soldier, t0, tries):
		try:
			idx = player.index
		except Exception:
			return 1
		if not self.alive(player):
			return 1
		r, s = self.root_of(player)
		if s is None:
			s = soldier
		if not self.is_soldier(r, s):
			self.st['vehicle'] += 1
			return 1
		try:
			pos = s.getPosition()
			self.calls += 1
		except Exception:
			return 0
		if pos is None or (abs(pos[0]) < 0.01 and abs(pos[2]) < 0.01):
			return 0
		# the nearest spawn point of any flag (main bases too, to tell them apart)
		best = None
		bestd = self.c['SPAWN_MATCH']
		for name, fk, x, h, z in KARKAND64_POINTS:
			d = _dist2(pos, (x, h, z))
			dh = pos[1] - h
			if d <= bestd and dh <= self.c['SPAWN_UP'] and dh >= -self.c['SPAWN_DOWN']:
				best = (name, fk, (x, h, z))
				bestd = d
		nm = self.name_of(player)
		if best is None:
			self.st['other'] += 1
			return 1
		name, fk, ppos = best
		if self.main_bases.get(fk):
			self.st['base'] += 1
			return 1
		f = self.flags.get(fk)
		if f is None or f['cp'] is None:
			self.st['other'] += 1
			return 1
		try:
			team = player.getTeam()
			self.calls += 1
		except Exception:
			return 1
		# a squad-leader spawn that happens to land on a flag point
		sl = self.squad_leader_near(player, team, pos)
		if sl:
			self.st['sl'] += 1
			self.log('%s spawned at %s next to his squad leader %s - not protected' % (nm, name, sl))
			return 1
		try:
			owner = f['cp'].cp_getParam('team')
			self.calls += 1
		except Exception:
			owner = team
		if owner != team:
			self.st['other'] += 1
			self.log('%s spawned at %s but %s reads team %s (his %s) - not protected' % (nm, name, f['label'], owner, team))
			return 1
		self.st['flag'] += 1
		if self.c['CAPTURE_OFF'] and self.flag_taking(f, team):
			self.st['taken'] += 1
			self.log('%s spawned at %s: %s is being taken - not protected' % (nm, name, f['label']))
			self.test_say('%s at %s: flag being taken, no protection' % (nm, f['label']))
			return 1
		hp = 100.0
		try:
			hp = float(s.getDamage())
			self.calls += 1
		except Exception:
			hp = 100.0
		if hp <= 0:
			hp = 100.0
		base_hp = hp
		target = hp
		if self.c['OVER_HP'] > 0:
			try:
				s.setDamage(float(self.c['OVER_HP']))
				self.calls += 1
				target = float(self.c['OVER_HP'])
				back = float(s.getDamage())
				self.calls += 1
				self.log('%s: OVER_HP %d set, health reads %.1f' % (nm, self.c['OVER_HP'], back))
				if back < target - 0.5:
					target = max(back, base_hp)
			except Exception:
				self.log('%s: OVER_HP could not be set: %s' % (nm, _err()))
		self.prot[idx] = {'player': player, 'soldier': s, 'name': nm, 'team': team, 'flag': fk,
			'point': name, 't0': _now(), 'start': pos, 'low': pos[1], 'base': base_hp, 'target': target,
			'hits': 0, 'hp': 0.0, 'said': 0}
		self.st['protected'] += 1
		self.log('%s (%s) protected at %s (%s, %.1f m from the point), health %.0f'
			% (nm, self.side(team), name, f['label'], bestd, hp))
		self.test_say('%s protected at %s' % (nm, name))
		return 1

	def side(self, team):
		if team == 1:
			return 'MEC'
		if team == 2:
			return 'US'
		return 'team %s' % team

	def squad_leader_near(self, player, team, pos):
		try:
			sq = player.getSquadId()
			lead = player.isSquadLeader()
			self.calls += 2
		except Exception:
			return None
		if not sq or lead:
			return None
		for p in self.players():
			try:
				if p.index == player.index:
					continue
				if p.getTeam() != team or p.getSquadId() != sq or not p.isSquadLeader():
					continue
				self.calls += 3
			except Exception:
				continue
			if not self.alive(p):
				continue
			r, s = self.root_of(p)
			try:
				q = r.getPosition()
				self.calls += 1
			except Exception:
				continue
			if _dist2(q, pos) <= self.c['SL_NEAR'] and abs(q[1] - pos[1]) < 4.0:
				return self.name_of(p)
		return None

	# ------------------------------------------------------------------ protection
	def end_prot(self, idx, why):
		r = self.prot.get(idx)
		if r is None:
			return
		del self.prot[idx]
		s = r['soldier']
		if r['target'] > r['base'] + 0.5:
			try:
				if self.alive(r['player']):
					hp = float(s.getDamage())
					self.calls += 1
					if hp > r['base']:
						s.setDamage(r['base'])
						self.calls += 1
			except Exception:
				self.log('%s: health not put back to %.0f: %s' % (r['name'], r['base'], _err()))
		e = self.st['ends']
		key = why.split(' (')[0]
		e[key] = e.get(key, 0) + 1
		self.log('%s: protection off after %.2f s - %s; hits %d, health given back %.0f'
			% (r['name'], _now() - r['t0'], why, r['hits'], r['hp']))
		self.test_say('%s: protection off - %s' % (r['name'], why))

	def protected(self, idx):
		r = self.prot.get(idx)
		if r is None:
			return None
		if _now() - r['t0'] > self.c['WINDOW'] + 0.05:
			return None
		return r

	def look_prot(self, now):
		for idx in list(self.prot.keys()):
			r = self.prot.get(idx)
			if r is None:
				continue
			p = r['player']
			if not self.alive(p):
				self.end_prot(idx, 'dead or down')
				continue
			if now - r['t0'] > self.c['WINDOW']:
				self.end_prot(idx, 'time (%.1f s)' % self.c['WINDOW'])
				continue
			s = r['soldier']
			# health first: a hit this frame is put back before anything else
			try:
				hp = float(s.getDamage())
				self.calls += 1
			except Exception:
				self.end_prot(idx, 'health could not be read')
				continue
			if hp > 0 and hp < r['target'] - 0.01:
				try:
					s.setDamage(r['target'])
					self.calls += 1
				except Exception:
					self.log('%s: health could not be put back: %s' % (r['name'], _err()))
				r['hits'] += 1
				r['hp'] += r['target'] - hp
				self.st['hits'] += 1
				self.st['hp'] += r['target'] - hp
				f = self.flags.get(r['flag'])
				self.log('%s hit while protected at %s: health %.0f, back to %.0f'
					% (r['name'], r['point'], hp, r['target']))
				if not r['said'] and self.c['CHAT_GUARD']:
					r['said'] = 1
					self.say(_fmt(self.c['MSG_GUARD'], {'victim': r['name'], 'flag': f['label'],
						'window': ('%.1f' % self.c['WINDOW']).rstrip('0').rstrip('.')}))
			# place: moved or jumped
			try:
				pos = s.getPosition()
				self.calls += 1
			except Exception:
				continue
			moved = _dist2(pos, r['start'])
			if moved > self.c['MOVE']:
				self.end_prot(idx, 'moved (%.2f m)' % moved)
				continue
			if pos[1] < r['low']:
				r['low'] = pos[1]
			if pos[1] - r['low'] > self.c['JUMP_UP']:
				self.end_prot(idx, 'jumped (%.2f m up)' % (pos[1] - r['low']))
				continue
		# the flags of the protected players
		if self.c['CAPTURE_OFF'] and self.prot:
			seen = {}
			for idx in list(self.prot.keys()):
				r = self.prot.get(idx)
				if r is None:
					continue
				key = (r['flag'], r['team'])
				if not (key) in seen:
					f = self.flags.get(r['flag'])
					if now - f['look'] >= self.c['CAPTURE_EVERY'] or f.get('look_team') != r['team']:
						f['look'] = now
						f['look_team'] = r['team']
						f['taking'] = self.flag_taking(f, r['team'])
					seen[key] = f['taking']
				if seen[key]:
					self.end_prot(idx, 'the enemy is taking %s' % self.flags[r['flag']]['label'])

	# ------------------------------------------------------------------ events
	def onPlayerKilled(self, victim, attacker, weapon, assists, obj):
		if 1 != self.__state or not self.active:
			return
		try:
			self.killed(victim, attacker, weapon)
		except Exception:
			self.log('PlayerKilled: ' + _err())

	def killed(self, victim, attacker, weapon):
		vi = None
		ai = None
		try:
			vi = victim.index
		except Exception:
			pass
		try:
			if attacker is not None:
				ai = attacker.index
		except Exception:
			ai = None
		# his own kill ends the killer's protection
		if ai is not None and ai != vi and (ai) in self.prot:
			self.end_prot(ai, 'his own kill')
		if vi is None:
			return
		r = self.protected(vi)
		if r is None:
			if (vi) in self.prot:
				self.end_prot(vi, 'dead')
			return
		vname = r['name']
		f = self.flags.get(r['flag'])
		wname = '?'
		try:
			wname = str(weapon.templateName)
		except Exception:
			wname = '?'
		self.end_prot(vi, 'killed')
		self.st['saved_kills'] += 1
		if attacker is None or ai is None or ai == vi:
			self.st['not_punished'] += 1
			self.log('%s died while protected at %s (%s), no killer - not punished' % (vname, r['point'], wname))
			return
		try:
			ateam = attacker.getTeam()
			self.calls += 1
		except Exception:
			ateam = -1
		aname = self.name_of(attacker)
		if ateam == r['team'] and not self.c['TEST_TK']:
			self.st['not_punished'] += 1
			self.log('%s killed his teammate %s while protected at %s (%s) - not punished' % (aname, vname, r['point'], wname))
			return
		wl = wname.lower()
		for w in self.skip:
			if wl.find(w) >= 0:
				self.st['not_punished'] += 1
				self.log('%s killed %s while protected at %s with %s - SKIP (%s), not punished' % (aname, vname, r['point'], wname, w))
				return
		if not self.c['PUNISH']:
			self.st['not_punished'] += 1
			self.log('%s killed %s while protected at %s with %s - PUNISH 0' % (aname, vname, r['point'], wname))
			return
		now = _now()
		d = self.doomed.get(ai)
		if d is not None and now < d['until']:
			self.st['not_punished'] += 1
			self.log('%s killed %s while protected at %s with %s - already punished (his vehicle is going down)' % (aname, vname, r['point'], wname))
			return
		lp = self.last_punish.get(ai)
		if lp is not None and now - lp < self.c['SAME_ATTACK']:
			self.st['not_punished'] += 1
			self.log('%s killed %s while protected at %s with %s - punished / warned %.1f s ago, once is enough' % (aname, vname, r['point'], wname, now - lp))
			return
		self.punish(attacker, ai, aname, vname, f['label'], r['point'], wname)

	def punish(self, attacker, ai, aname, vname, flag, point, wname):
		now = _now()
		if not self.alive(attacker):
			self.st['not_punished'] += 1
			self.log('%s killed %s while protected at %s with %s - already dead or down, nothing done' % (aname, vname, point, wname))
			return
		root, soldier = self.root_of(attacker)
		self.last_punish[ai] = now
		if not self.is_soldier(root, soldier):
			# a vehicle or a gun: warnings first (VEH_WARNINGS a round), then it is destroyed
			n = self.veh_warned.get(ai, 0)
			if n < self.c['VEH_WARNINGS']:
				n += 1
				self.veh_warned[ai] = n
				self.st['warned'] += 1
				tpl = self.template(root)
				self.log('WARN %s (in %s, %s) %d/%d for killing %s while protected at %s - the next time it is destroyed'
					% (aname, tpl, wname, n, self.c['VEH_WARNINGS'], vname, point))
				self.say(_fmt(self.c['MSG_VEH_WARN'], {'killer': aname, 'victim': vname, 'flag': flag,
					'vehicle': _pretty_vehicle(tpl), 'n': n, 'max': self.c['VEH_WARNINGS']}))
				return
		self.st['punished'] += 1
		if self.is_soldier(root, soldier):
			ok = self.kill_soldier(attacker, soldier, aname)
			self.keep_down[ai] = now + self.c['KEEP_DOWN']
			self.log('PUNISH %s (on foot, %s) for killing %s while protected at %s: %s'
				% (aname, wname, vname, point, ok))
			self.say(_fmt(self.c['MSG_KILL'], {'killer': aname, 'victim': vname, 'flag': flag}))
		else:
			tpl = self.template(root)
			vlabel = _pretty_vehicle(tpl)
			how = 'parachute - killed when he lands'
			if tpl.lower().find('parachute') < 0:
				how = self.set_vehicle_hp(root, soldier, self.c['VEH_HP_LEFT'], tpl)
			self.doomed[ai] = {'until': now + self.c['VEH_GRACE'], 'tpl': tpl, 'name': aname}
			self.log('PUNISH %s (in %s, %s) for killing %s while protected at %s: %s'
				% (aname, tpl, wname, vname, point, how))
			msg = self.c['MSG_VEH']
			if how.find('could NOT') >= 0 or how.startswith('parachute'):
				msg = self.c['MSG_LATER']
			self.say(_fmt(msg, {'killer': aname, 'victim': vname, 'flag': flag, 'vehicle': vlabel}))
		self.later.append((now + self.c['CHECK_AFTER'], self.check_after, (attacker, aname)))

	def kill_soldier(self, player, soldier, name):
		try:
			before = float(soldier.getDamage())
			soldier.setDamage(0.0)
			self.calls += 2
			return 'health %.0f -> 0' % before
		except Exception:
			return 'could NOT be killed: ' + _err()

	def set_vehicle_hp(self, veh, soldier, value, tpl):
		"""Set a vehicle's health; its own calls, else the soldier's calls used on it."""
		way = self.veh_way.get(tpl)
		tries = []
		if way is None or way == 'own':
			tries.append('own')
		if way is None or way == 'im_func':
			tries.append('im_func')
		if way is None or way == 'class':
			tries.append('class')
		shp = None
		try:
			shp = float(soldier.getDamage())
			self.calls += 1
		except Exception:
			shp = None
		notes = []
		for t in tries:
			get = None
			put = None
			try:
				if t == 'own':
					get = getattr(veh, 'getDamage', None)
					put = getattr(veh, 'setDamage', None)
					if get is None or put is None:
						notes.append('own: none')
						continue
					g = lambda: get()
					pfun = lambda v: put(v)
				elif t == 'im_func':
					gm = getattr(soldier.getDamage, 'im_func', None)
					pm = getattr(soldier.setDamage, 'im_func', None)
					if gm is None or pm is None:
						notes.append('im_func: none (%s)' % repr(soldier.getDamage)[:60])
						continue
					g = lambda: gm(veh)
					pfun = lambda v: pm(veh, v)
				else:
					cls = getattr(soldier, '__class__', None)
					gm = getattr(cls, 'getDamage', None)
					pm = getattr(cls, 'setDamage', None)
					if gm is None or pm is None:
						notes.append('class: none')
						continue
					g = lambda: gm(veh)
					pfun = lambda v: pm(veh, v)
				hp = float(g())
				self.calls += 1
			except Exception:
				notes.append('%s: read failed (%s)' % (t, _err()))
				continue
			if not (hp > 0 and hp <= 20000):
				notes.append('%s: read %.1f - not a vehicle health' % (t, hp))
				continue
			if t != 'own' and shp is not None and abs(hp - shp) < 0.01 and hp <= 100.0:
				notes.append('%s: read %.1f = the soldier\'s own - not used' % (t, hp))
				continue
			try:
				pfun(float(value))
				self.calls += 1
				after = float(g())
				self.calls += 1
			except Exception:
				notes.append('%s: set failed (%s)' % (t, _err()))
				continue
			if shp is not None:
				try:
					s2 = float(soldier.getDamage())
					self.calls += 1
					if abs(s2 - shp) > 0.01:
						soldier.setDamage(shp)
						notes.append('%s: the SOLDIER changed %.0f -> %.0f, put back' % (t, shp, s2))
						continue
				except Exception:
					pass
			self.veh_way[tpl] = t
			notes.append('health %.0f -> %.1f (%s calls)' % (hp, after, t))
			return '; '.join(notes)
		self.veh_way[tpl] = 'none'
		notes.append('its health could NOT be set - he is killed when he gets out')
		return '; '.join(notes)

	def check_after(self, attacker, aname):
		try:
			if not attacker.isValid():
				self.log('check: %s has left' % aname)
				return
		except Exception:
			pass
		al = 0
		down = 0
		try:
			al = attacker.isAlive()
			down = attacker.isManDown()
			self.calls += 2
		except Exception:
			pass
		where = 'on foot'
		if al and not down:
			root, soldier = self.root_of(attacker)
			if not self.is_soldier(root, soldier):
				where = 'in %s' % self.template(root)
		self.log('check %.0f s after punishing %s: %s' % (self.c['CHECK_AFTER'], aname,
			(al and not down) and ('ALIVE ' + where) or (down and 'man down' or 'dead')))

	def onEnterVehicle(self, player, vehicle, freeSoldier=False):
		if 1 != self.__state or not self.active:
			return
		try:
			idx = player.index
			if (idx) in self.prot:
				self.end_prot(idx, 'into %s' % self.template(vehicle))
		except Exception:
			self.log('EnterVehicle: ' + _err())

	def onExitVehicle(self, player, vehicle):
		if 1 != self.__state or not self.active:
			return
		try:
			idx = player.index
			d = self.doomed.get(idx)
			if d is not None and _now() < d['until']:
				self.later.append((_now() + 0.3, self.kill_on_exit, (player, d)))
		except Exception:
			self.log('ExitVehicle: ' + _err())

	def kill_on_exit(self, player, d):
		if not self.alive(player):
			return
		root, soldier = self.root_of(player)
		if not self.is_soldier(root, soldier):
			return
		ok = self.kill_soldier(player, soldier, d['name'])
		try:
			self.keep_down[player.index] = _now() + self.c['KEEP_DOWN']
		except Exception:
			pass
		self.log('%s got out of his punished %s: killed on foot (%s)' % (d['name'], d['tpl'], ok))

	def onPlayerRevived(self, victim, attacker):
		if 1 != self.__state or not self.active:
			return
		try:
			idx = victim.index
			until = self.keep_down.get(idx)
			if until is not None and _now() < until:
				self.later.append((_now() + 0.1, self.put_down, (victim,)))
		except Exception:
			self.log('PlayerRevived: ' + _err())

	def put_down(self, victim):
		if not self.alive(victim):
			return
		root, soldier = self.root_of(victim)
		if not self.is_soldier(root, soldier):
			return
		ok = self.kill_soldier(victim, soldier, self.name_of(victim))
		self.log('%s revived after his punishment: put down again (%s)' % (self.name_of(victim), ok))

	def onPlayerDeath(self, player, vehicle):
		if 1 != self.__state:
			return
		try:
			self.forget(player, 1)
		except Exception:
			pass

	def onPlayerChangeTeams(self, player, humanHasSpawned):
		if 1 != self.__state:
			return
		try:
			self.forget(player, 1)
		except Exception:
			pass

	def onPlayerDisconnect(self, player):
		if 1 != self.__state:
			return
		try:
			if player.index in self.veh_warned:
				del self.veh_warned[player.index]
			self.forget(player, 1)
		except Exception:
			pass

	def forget(self, player, all):
		try:
			idx = player.index
		except Exception:
			return
		if (idx) in self.prot:
			self.end_prot(idx, 'dead or gone')
		if all:
			if (idx) in self.doomed:
				del self.doomed[idx]
		keep = []
		for e in self.pending:
			try:
				if e[0].index != idx:
					keep.append(e)
			except Exception:
				pass
		self.pending = keep

	# ------------------------------------------------------------------ frame
	def update(self):
		if 1 != self.__state:
			return
		if not self.prot and not self.later and not self.pending:
			return
		try:
			now = _now()
			if self.pending:
				self.look_pending()
			if self.prot:
				self.look_prot(now)
			if self.later:
				due = []
				keep = []
				for e in self.later:
					if e[0] <= now:
						due.append(e)
					else:
						keep.append(e)
				self.later = keep
				for t, fn, args in due:
					try:
						fn(*args)
					except Exception:
						self.log('later %s: %s' % (getattr(fn, '__name__', '?'), _err()))
		except Exception:
			self.log('update: ' + _err())

	# ------------------------------------------------------------------ test commands
	def onChatMessage(self, playerid, text, channel, flags):
		if 1 != self.__state or not self.c.get('TEST_COMMANDS', 0):
			return
		try:
			t = str(text).strip()
			changed = 1
			while changed:
				changed = 0
				for pre in CHAT_PREFIXES:
					if t.startswith(pre):
						t = t[len(pre):].strip()
						changed = 1
			if not t.lower().startswith('!ss'):
				return
			p = None
			try:
				p = bf2.playerManager.getPlayerByIndex(playerid)
			except Exception:
				p = None
			if p is None or not self.allowed(p):
				return
			self.command(p, t[3:].strip())
		except Exception:
			self.log('ChatMessage: ' + _err())

	def allowed(self, p):
		if not self.admins:
			return 0
		if '*' in self.admins:
			return 1
		n = self.name_of(p).lower()
		for a in self.admins:
			if n == a or n.endswith(' ' + a) or n.endswith(a):
				return 1
		return 0

	def command(self, p, args):
		a = args.split()
		nm = self.name_of(p)
		if not a:
			self.say('[SpawnSafe] %s: active %d, protected now %d, warned %d, punished %d this round; WINDOW %.1f, OVER_HP %d, VEH_WARNINGS %d, TEST_TK %d'
				% (VERSION_TEXT, self.active, len(self.prot), self.st['warned'], self.st['punished'], self.c['WINDOW'], self.c['OVER_HP'],
				self.c['VEH_WARNINGS'], self.c['TEST_TK']))
			return
		cmd = a[0].lower()
		if cmd == 'me':
			r, s = self.root_of(p)
			if not self.is_soldier(r, s) or not self.alive(p):
				self.say('[SpawnSafe] %s: on foot and alive, please' % nm)
				return
			pos = s.getPosition()
			best = None
			bestd = 1e9
			for name, fk, pp in self.points:
				d = _dist2(pos, pp)
				if d < bestd:
					best = (name, fk)
					bestd = d
			if best is None:
				self.say('[SpawnSafe] no protected flags on this map')
				return
			hp = float(s.getDamage())
			target = hp
			if self.c['OVER_HP'] > 0:
				s.setDamage(float(self.c['OVER_HP']))
				target = float(s.getDamage())
			self.prot[p.index] = {'player': p, 'soldier': s, 'name': nm, 'team': p.getTeam(), 'flag': best[1],
				'point': best[0] + ' (!ss me)', 't0': _now(), 'start': pos, 'low': pos[1], 'base': hp,
				'target': target, 'hits': 0, 'hp': 0.0, 'said': 0}
			self.st['protected'] += 1
			self.log('%s: !ss me - protected as at %s (%.0f m away), health %.0f, held at %.0f' % (nm, best[0], bestd, hp, target))
			self.say('[SpawnSafe] %s protected for %.1f s (as at %s); do not move' % (nm, self.c['WINDOW'], best[0]))
		elif cmd == 'hurt':
			n = 30.0
			if len(a) > 1:
				n = _f(a[1], 30.0)
			r, s = self.root_of(p)
			hp = float(s.getDamage())
			s.setDamage(max(1.0, hp - n))
			self.log('%s: !ss hurt %.0f - health %.0f -> %.0f' % (nm, n, hp, max(1.0, hp - n)))
		elif cmd == 'hp':
			if len(a) > 1:
				self.c['OVER_HP'] = _i(a[1], 0)
			self.say('[SpawnSafe] OVER_HP %d' % self.c['OVER_HP'])
		elif cmd == 'tk':
			if len(a) > 1:
				self.c['TEST_TK'] = (a[1].lower() in ('on', '1')) and 1 or 0
			self.say('[SpawnSafe] TEST_TK %d (a teammate\'s kill counts as an enemy\'s)' % self.c['TEST_TK'])
		elif cmd == 'window':
			if len(a) > 1:
				self.c['WINDOW'] = _f(a[1], self.c['WINDOW'])
			self.say('[SpawnSafe] WINDOW %.1f s' % self.c['WINDOW'])
		elif cmd == 'pos':
			r, s = self.root_of(p)
			try:
				pos = r.getPosition()
			except Exception:
				return
			best = None
			bestd = 1e9
			for name, fk, x, h, z in KARKAND64_POINTS:
				d = _dist2(pos, (x, h, z))
				if d < bestd:
					best = (name, h)
					bestd = d
			msg = '[SpawnSafe] %s at %.1f %.1f %.1f; nearest point %s %.1f m away (%.1f m up)' % (
				nm, pos[0], pos[1], pos[2], best[0], bestd, pos[1] - best[1])
			self.log(msg)
			self.say(msg)
		elif cmd == 'flag':
			r, s = self.root_of(p)
			pos = r.getPosition()
			best = None
			bestd = 1e9
			for k in self.flags.keys():
				f = self.flags[k]
				d = _dist2(pos, f['pos'])
				if d < bestd:
					best = f
					bestd = d
			if best is None:
				return
			team = p.getTeam()
			msg = '[SpawnSafe] %s: being taken from %s = %d (owner %s)' % (best['label'], self.side(team),
				self.flag_taking(best, team), best['cp'] and best['cp'].cp_getParam('team'))
			self.log(msg)
			self.say(msg)
		else:
			self.say('[SpawnSafe] !ss | !ss me | !ss hurt [n] | !ss hp <n> | !ss tk on|off | !ss window <s> | !ss pos | !ss flag')

	# ------------------------------------------------------------------ ModManager
	def init(self):
		self.load_config()
		if 0 == self.__state:
			host.registerHandler('PlayerSpawn', self.onPlayerSpawn, 1)
			host.registerHandler('PlayerKilled', self.onPlayerKilled, 1)
			host.registerHandler('PlayerDeath', self.onPlayerDeath, 1)
			host.registerHandler('EnterVehicle', self.onEnterVehicle, 1)
			host.registerHandler('ExitVehicle', self.onExitVehicle, 1)
			host.registerHandler('PlayerRevived', self.onPlayerRevived, 1)
			host.registerHandler('PlayerChangeTeams', self.onPlayerChangeTeams, 1)
			host.registerHandler('PlayerDisconnect', self.onPlayerDisconnect, 1)
			host.registerHandler('ChatMessage', self.onChatMessage, 1)
			host.registerGameStatusHandler(self.onGameStatusChanged)
		self.mm.registerUpdates(self.update)
		self.__state = 1
		self.log('spawnsafe %s loaded (WINDOW %.1f s, MOVE %.2f m, CAPTURE_OFF %d, PUNISH %d, VEH_WARNINGS %d, SKIP "%s", TEST_COMMANDS %d)'
			% (VERSION_TEXT, self.c['WINDOW'], self.c['MOVE'], self.c['CAPTURE_OFF'], self.c['PUNISH'],
			self.c['VEH_WARNINGS'], self.c['SKIP'], self.c['TEST_COMMANDS']))
		# loaded during a round
		try:
			if self.mm.currentGameStatus == bf2.GameStatus.Playing:
				self.round_start()
		except Exception:
			pass

	def shutdown(self):
		try:
			for idx in list(self.prot.keys()):
				self.end_prot(idx, 'module shut down')
		except Exception:
			pass
		try:
			self.mm.unregisterUpdates(self.update)
		except Exception:
			pass
		try:
			host.unregisterGameStatusHandler(self.onGameStatusChanged)
		except Exception:
			pass
		self.__state = 2
		self.log('spawnsafe shut down')
		try:
			if self.logf is not None:
				self.logf.close()
		except Exception:
			pass
		self.logf = None


def mm_load(modManager):
	return SpawnSafe(modManager)
