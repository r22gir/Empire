// Minimal single-instance React hook shim for scripts/check-chat-queue.sh (not shipped).
const cells = [];
let i = 0;
exports.__reset = () => { cells.length = 0; i = 0; };
exports.__state = cells;
exports.useState = (init) => {
  const k = i++;
  if (!(k in cells)) cells[k] = { v: typeof init === 'function' ? init() : init };
  const cell = cells[k];
  const set = (u) => { cell.v = typeof u === 'function' ? u(cell.v) : u; };
  return [cell.v, set, cell];
};
exports.useRef = (init) => { const k = i++; if (!(k in cells)) cells[k] = { current: init }; return cells[k]; };
exports.useCallback = (fn) => fn;
exports.useEffect = () => {};
exports.useMemo = (fn) => fn();
