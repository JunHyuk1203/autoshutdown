// Policy-expression regression tests. Firebase emulator/deployment validation remains separate.
const assert = require('node:assert/strict');
const fs = require('fs');
const rules = JSON.parse(fs.readFileSync(require('path').join(__dirname, '..', 'database.rules.json'))).rules;
const teacher = { uid: 'teacher', token: { email: 'teacher@example.test', email_verified: true } };
const pending = { uid: 'pending', token: { email: 'pending@example.test', email_verified: true } };
const device = { uid: 'device', token: { pc_id: 'PC_01' } };
const master = { uid: 'master', token: { email: 'tntgame1203@gmail.com', email_verified: true } };
function snapshot(value) {
  return { val: () => value ?? null, exists: () => value != null,
    child: key => snapshot(value?.[key]), isString: () => typeof value === 'string',
    isNumber: () => typeof value === 'number', hasChildren: keys => keys.every(key => value?.[key] != null) };
}
const root = snapshot({ users: { teacher: { approved: true } } });
function evaluate(expression, auth, vars, value) {
  if (typeof expression === 'boolean') return expression;
  return Function('auth', 'root', 'newData', '$pc_id', '$uid', '$cmd_id', `return !!(${expression});`)(
    auth, root, snapshot(value), vars.$pc_id, vars.$uid, vars.$cmd_id);
}
function allowed(action, path, auth, value = {}) {
  let node = rules, vars = {};
  if (evaluate(node['.' + action], auth, vars, value)) return true;
  for (const part of path.split('/')) {
    if (node[part]) node = node[part];
    else {
      const key = Object.keys(node).find(key => key.startsWith('$'));
      if (!key) return false;
      vars[key] = part;
      node = node[key];
    }
    if (node['.' + action] !== undefined && evaluate(node['.' + action], auth, vars, value)) return true;
  }
  return false;
}
let count = 0;
function check(expected, ...args) { assert.equal(allowed(...args), expected, args.slice(0, 2).join(' ')); count++; }
for (const path of ['commands/PC_01', 'commands/PC_01/command', 'commands/__ALL__', 'update_info']) {
  check(false, 'write', path, null);
}
check(false, 'write', 'update_info', null, null);
for (const path of ['pcs/PC_01', 'screenshots/PC_01', 'explorer/PC_01', 'explorer_favorites/PC_01']) check(true, 'write', path, null);
for (const path of ['commands/PC_01', 'commands/PC_01/command', 'commands/__ALL__']) {
  check(true, 'read', path, null);
  check(true, 'write', path, null, null);
}
for (const auth of [null, pending]) {
  for (const path of ['pcs', 'screenshots/PC_01', 'explorer/PC_01']) check(false, 'read', path, auth);
}
check(true, 'read', 'pcs', teacher);
check(true, 'read', 'screenshots/PC_01', master);
check(true, 'read', 'commands/PC_01', device);
check(true, 'read', 'commands/PC_02', device);
check(true, 'read', 'commands/__ALL__', device);
check(true, 'write', 'pcs/PC_01', device);
check(true, 'write', 'pcs/PC_02', device);
check(true, 'write', 'pcs/PC_01', teacher);
check(true, 'write', 'pcs/PC_01', teacher, null);
check(false, 'write', 'commands/PC_01', device);
check(true, 'write', 'commands/PC_01', device, null);
check(true, 'write', 'commands/PC_01/id', device, null);
check(true, 'write', 'commands/PC_02/id', device, null);
check(true, 'write', 'commands/__ALL__', device, null);
check(true, 'write', 'commands/PC_01', teacher);
check(true, 'write', 'update_info', master);
check(false, 'write', 'update_info', teacher);
check(false, 'write', 'update_info', device);
check(false, 'write', 'users/pending/approved', pending, true);
check(true, 'write', 'users/teacher/approved', teacher, false);
check(false, 'write', 'users/teacher/approved', teacher, true);
check(true, 'write', 'users/teacher/approved', master, true);
check(false, 'write', 'users/master', { uid: 'x', token: { email: master.token.email, email_verified: false } });
check(true, 'write', 'pending_users/pending', pending);
check(true, 'write', 'pending_users/pending', master, null);
console.log(`Firebase policy expression tests passed: ${count} access cases (not an emulator test).`);
