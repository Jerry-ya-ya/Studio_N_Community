export const INTRO_DURATION = 6900;

const STAGE_STARTS = [0, 1630, 3240, 4770];
const CAMERAS = [
  { x: 36, span: 176 },
  { x: 36, span: 106 },
  { x: 48, span: 60 },
  { x: 54, span: 31 }
];

const SETS = [
  { symbol: 'A', x: 36, radiusX: 46, radiusY: 27, color: '#75dcb6', fill: 'rgba(77, 172, 135, .09)' },
  { symbol: 'B', x: 48, radiusX: 25, radiusY: 16, color: '#83e4ef', fill: 'rgba(80, 189, 205, .10)' },
  { symbol: 'C', x: 54, radiusX: 12, radiusY: 8, color: '#d7ff9e', fill: 'rgba(160, 222, 104, .13)' }
];

const STUDENT_DIRECTIONS = [180, 225, 270, 315, 0, 45, 90, 135, 205, 340, 65, 155].map(degrees => {
  const radians = degrees * Math.PI / 180;
  return { x: Math.cos(radians), y: Math.sin(radians) };
});
const MOVES = [
  { start: 540, duration: 1380, radiusFraction: .94 },
  { start: 2300, duration: 1180, radiusFraction: .87 },
  { start: 3930, duration: 1280, radiusFraction: .50 }
];

function ease(progress: number): number {
  const t = Math.max(0, Math.min(1, progress));
  return t * t * (3 - 2 * t);
}

function interpolate(from: number, to: number, progress: number): number {
  return from + (to - from) * progress;
}

export function stageAt(elapsed: number): number {
  return STAGE_STARTS.filter(start => elapsed >= start).length - 1;
}

function studentPosition(index: number, elapsed: number) {
  const time = elapsed - index * 55;
  const direction = STUDENT_DIRECTIONS[index];
  const outer = SETS[0];
  let x = outer.x + direction.x * outer.radiusX * 1.5;
  let y = direction.y * outer.radiusY * 1.5;

  for (const [stage, move] of MOVES.entries()) {
    const set = SETS[stage];
    const progress = ease((time - move.start) / move.duration);
    x = interpolate(x, set.x + direction.x * set.radiusX * move.radiusFraction, progress);
    y = interpolate(y, direction.y * set.radiusY * move.radiusFraction, progress);
  }
  return { x, y };
}

export function drawIntro(context: CanvasRenderingContext2D, elapsed: number, stage: number): void {
  const { canvas } = context;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const density = Math.min(window.devicePixelRatio || 1, 2);
  const pixelWidth = Math.round(width * density);
  const pixelHeight = Math.round(height * density);
  if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
    canvas.width = pixelWidth;
    canvas.height = pixelHeight;
  }
  if (!width || !height) {
    return;
  }

  const target = CAMERAS[stage];
  const previous = CAMERAS[Math.max(0, stage - 1)];
  const zoom = ease((elapsed - STAGE_STARTS[stage]) / 1080);
  const center = interpolate(previous.x, target.x, zoom);
  const span = interpolate(previous.span, target.span, zoom);
  const scale = Math.min(width / span, height * 2 / span);
  const projectX = (x: number) => width / 2 + (x - center) * scale;
  const projectY = (y: number) => height / 2 - y * scale;

  context.setTransform(density, 0, 0, density, 0, 0);
  context.clearRect(0, 0, width, height);
  drawGrid(context, width, height, projectX(0), projectY(0), scale);

  for (const [index, set] of SETS.entries()) {
    const isActive = index === stage - 1;
    const x = projectX(set.x);
    const y = projectY(0);
    context.globalAlpha = isActive ? 1 : index < stage - 1 ? .26 : .52;
    context.beginPath();
    context.ellipse(x, y, set.radiusX * scale, set.radiusY * scale, 0, 0, Math.PI * 2);
    context.fillStyle = set.fill;
    context.fill();
    context.strokeStyle = set.color;
    context.lineWidth = isActive ? 2 : 1;
    context.stroke();
    context.fillStyle = set.color;
    context.font = '600 12px ui-monospace, monospace';
    context.fillText(set.symbol, x - 4, y - set.radiusY * scale + 17);
  }
  context.globalAlpha = 1;

  // Draw X₁ last so it stays readable as the points converge.
  for (let index = STUDENT_DIRECTIONS.length - 1; index >= 0; index--) {
    const lead = index === 0;
    const { x, y } = studentPosition(index, elapsed);
    const px = projectX(x);
    const py = projectY(y);
    context.beginPath();
    for (let sample = 6; sample >= 0; sample--) {
      const trail = studentPosition(index, elapsed - sample * 36);
      context.lineTo(projectX(trail.x), projectY(trail.y));
    }
    context.strokeStyle = lead ? 'rgba(215, 255, 158, .42)' : 'rgba(129, 230, 186, .24)';
    context.lineWidth = lead ? 2 : 1;
    context.stroke();

    context.beginPath();
    context.arc(px, py, lead ? 5 : 2.7, 0, Math.PI * 2);
    context.fillStyle = lead ? '#e5ffaf' : '#81e6ba';
    context.shadowColor = context.fillStyle;
    context.shadowBlur = lead ? 18 : 7;
    context.fill();
    context.shadowBlur = 0;

    if (lead || (stage === 0 && (index === 1 || index === STUDENT_DIRECTIONS.length - 1))) {
      const label = lead ? 'X₁' : index === 1 ? 'X₂' : 'Xₙ';
      context.font = '600 14px ui-monospace, monospace';
      context.fillText(label, px + 9, py - 8);
    }
  }
}

function drawGrid(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  originX: number,
  originY: number,
  scale: number
): void {
  const step = scale * 5;
  context.beginPath();
  for (let x = originX % step; x < width; x += step) {
    context.moveTo(x, 0);
    context.lineTo(x, height);
  }
  for (let y = originY % step; y < height; y += step) {
    context.moveTo(0, y);
    context.lineTo(width, y);
  }
  context.strokeStyle = 'rgba(131, 208, 173, .11)';
  context.lineWidth = 1;
  context.stroke();

  context.beginPath();
  context.moveTo(0, originY);
  context.lineTo(width, originY);
  context.moveTo(originX, 0);
  context.lineTo(originX, height);
  context.strokeStyle = 'rgba(131, 208, 173, .35)';
  context.stroke();
  context.fillStyle = '#8ab3a1';
  context.font = '12px ui-monospace, monospace';
  context.fillText('x', width - 18, originY - 8);
  context.fillText('y', originX + 8, 18);
}
