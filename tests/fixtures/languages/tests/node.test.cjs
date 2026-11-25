const assert = require('node:assert/strict');
const test = require('node:test');

test('Node.js has its built-in fetch API', () => {
  assert.equal(typeof fetch, 'function');
});
