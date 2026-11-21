import React from 'react';
import {
	AbsoluteFill,
	interpolate,
	interpolateColors,
	spring,
	useCurrentFrame,
	useVideoConfig,
	Easing,
} from 'remotion';

// ---------- Paleta ----------
const C = {
	bgDay: '#0E2236',
	bgNight: '#050B14',
	sun: '#FFC83D',
	dc: '#FFC83D', // corriente continua
	ac: '#3DDC97', // corriente alterna
	grid: '#5AB4FF',
	wire: '#2C4560',
	text: '#F4F7FA',
	muted: '#9FB3C8',
	alert: '#FF5A5F',
	panel: '#1F4E8C',
	house: '#E8EEF4',
};

const FONT = 'Inter, "Inter Display", system-ui, sans-serif';

// ---------- Línea de tiempo (frames @30 fps) ----------
const T = {
	hookB: 60, // se va la luz
	q: 120, // pregunta
	panel: 210,
	inverter: 420,
	house: 630,
	exportStart: 840,
	night: 960,
	blackoutScene: 1050,
	gridFail: 1110,
	invOff: 1150,
	end: 1260,
	battery: 1290,
};

const inRange = (f: number, a: number, b: number) => f >= a && f < b;

const fadeWindow = (f: number, a: number, b: number, d = 10) =>
	interpolate(f, [a, a + d, b - d, b], [0, 1, 1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

// ---------- Geometría ----------
type Pt = [number, number];
const P = {
	sun: [190, 860] as Pt,
	panel: [190, 1180] as Pt,
	inverter: [430, 1200] as Pt,
	house: [690, 1160] as Pt,
	meter: [860, 1340] as Pt,
	tower: [975, 1150] as Pt,
	battery: [430, 1500] as Pt,
};

const PATH_PANEL_INV: Pt[] = [
	[190, 1250],
	[190, 1340],
	[410, 1340],
	[410, 1285],
];
const PATH_INV_HOUSE: Pt[] = [
	[450, 1285],
	[450, 1340],
	[690, 1340],
	[690, 1262],
];
const PATH_HOUSE_GRID: Pt[] = [
	[690, 1340],
	[975, 1340],
	[975, 1270],
];
const PATH_BAT_HOUSE: Pt[] = [
	[430, 1462],
	[430, 1288],
];

const polyLen = (pts: Pt[]) =>
	pts.slice(1).reduce((s, p, i) => s + Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]), 0);

const pointAt = (pts: Pt[], t: number): Pt => {
	const total = polyLen(pts);
	let d = t * total;
	for (let i = 1; i < pts.length; i++) {
		const a = pts[i - 1];
		const b = pts[i];
		const seg = Math.hypot(b[0] - a[0], b[1] - a[1]);
		if (d <= seg) {
			const k = seg === 0 ? 0 : d / seg;
			return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k];
		}
		d -= seg;
	}
	return pts[pts.length - 1];
};

const toD = (pts: Pt[]) => pts.map((p, i) => `${i ? 'L' : 'M'}${p[0]},${p[1]}`).join(' ');

// ---------- Flujo de energía (partículas) ----------
const Flow: React.FC<{
	pts: Pt[];
	color: string;
	active: number; // 0..1 opacidad
	reverse?: boolean;
	speed?: number; // px por frame
	n?: number;
}> = ({pts, color, active, reverse, speed = 6, n = 7}) => {
	const f = useCurrentFrame();
	if (active <= 0.01) return null;
	const len = polyLen(pts);
	return (
		<g opacity={active}>
			{Array.from({length: n}).map((_, i) => {
				let t = ((f * speed) / len + i / n) % 1;
				if (reverse) t = 1 - t;
				const [x, y] = pointAt(pts, t);
				return (
					<g key={i}>
						<circle cx={x} cy={y} r={14} fill={color} opacity={0.25} />
						<circle cx={x} cy={y} r={7} fill={color} />
					</g>
				);
			})}
		</g>
	);
};

// ---------- Elementos del diagrama ----------
const Sun: React.FC<{y: number; opacity: number}> = ({y, opacity}) => {
	const f = useCurrentFrame();
	const rot = f * 0.6;
	return (
		<g transform={`translate(${P.sun[0]},${y})`} opacity={opacity}>
			<circle r={110} fill={C.sun} opacity={0.12} />
			<g transform={`rotate(${rot})`}>
				{Array.from({length: 12}).map((_, i) => (
					<rect
						key={i}
						x={-5}
						y={-92}
						width={10}
						height={26}
						rx={5}
						fill={C.sun}
						transform={`rotate(${i * 30})`}
					/>
				))}
			</g>
			<circle r={56} fill={C.sun} />
		</g>
	);
};

const Photons: React.FC<{opacity: number}> = ({opacity}) => {
	const f = useCurrentFrame();
	if (opacity <= 0.01) return null;
	return (
		<g opacity={opacity}>
			{Array.from({length: 5}).map((_, i) => {
				const t = ((f + i * 9) % 45) / 45;
				const x = P.sun[0] - 50 + i * 25;
				const y = interpolate(t, [0, 1], [950, 1110]);
				return (
					<line
						key={i}
						x1={x}
						y1={y}
						x2={x}
						y2={y + 26}
						stroke={C.sun}
						strokeWidth={6}
						strokeLinecap="round"
						opacity={1 - t * 0.6}
					/>
				);
			})}
		</g>
	);
};

const Glow: React.FC<{at: Pt; r: number; on: number; color?: string}> = ({
	at,
	r,
	on,
	color = C.text,
}) => {
	const f = useCurrentFrame();
	if (on <= 0.01) return null;
	const pulse = 1 + Math.sin(f / 6) * 0.05;
	return (
		<circle
			cx={at[0]}
			cy={at[1]}
			r={r * pulse}
			fill="none"
			stroke={color}
			strokeWidth={4}
			strokeDasharray="10 12"
			opacity={0.7 * on}
		/>
	);
};

const Panel: React.FC = () => (
	<g transform={`translate(${P.panel[0]},${P.panel[1]})`}>
		<rect x={-8} y={30} width={16} height={45} fill={C.wire} />
		<g transform="skewX(-12)">
			<rect x={-95} y={-65} width={190} height={110} rx={8} fill={C.panel} stroke="#8FB8E8" strokeWidth={4} />
			{[0, 1, 2].map((c) =>
				[0, 1].map((r) => (
					<rect
						key={`${c}-${r}`}
						x={-85 + c * 59}
						y={-56 + r * 49}
						width={52}
						height={42}
						fill="#2E6BC0"
						stroke="#8FB8E8"
						strokeWidth={1.5}
					/>
				)),
			)}
		</g>
	</g>
);

const Inverter: React.FC<{on: boolean; off: number}> = ({on, off}) => (
	<g transform={`translate(${P.inverter[0]},${P.inverter[1]})`}>
		<rect x={-70} y={-85} width={140} height={170} rx={16} fill="#24384F" stroke="#7E95AE" strokeWidth={4} />
		<rect x={-45} y={-60} width={90} height={50} rx={6} fill="#0B1622" />
		<text
			x={0}
			y={-26}
			textAnchor="middle"
			fontFamily={FONT}
			fontWeight={800}
			fontSize={26}
			fill={on ? C.ac : C.alert}
		>
			{on ? 'ON' : 'OFF'}
		</text>
		{/* símbolo CC → CA */}
		<line x1={-40} y1={25} x2={-12} y2={25} stroke={C.dc} strokeWidth={5} strokeLinecap="round" />
		<path d="M10,25 q8,-18 16,0 t16,0" stroke={C.ac} strokeWidth={5} fill="none" strokeLinecap="round" />
		<circle cx={0} cy={62} r={8} fill={on ? C.ac : C.alert} opacity={0.5 + off * 0.5} />
	</g>
);

const House: React.FC<{lit: number}> = ({lit}) => {
	const win = interpolateColors(lit, [0, 1], ['#26323F', '#FFD86B']);
	return (
		<g transform={`translate(${P.house[0]},${P.house[1]})`}>
			<circle r={150} fill="#FFD86B" opacity={0.08 * lit} />
			<path d="M-115,-10 L0,-110 L115,-10 Z" fill="#C9D4DF" />
			<rect x={-95} y={-12} width={190} height={115} fill={C.house} />
			<rect x={-70} y={10} width={50} height={45} rx={4} fill={win} />
			<rect x={20} y={10} width={50} height={45} rx={4} fill={win} />
			<rect x={-20} y={50} width={40} height={53} rx={4} fill="#7A8796" />
		</g>
	);
};

const Meter: React.FC<{dir: number}> = ({dir}) => {
	// dir: 1 exporta, -1 importa, 0 quieto
	const f = useCurrentFrame();
	const ang = (f * 8 * dir) % 360;
	return (
		<g transform={`translate(${P.meter[0]},${P.meter[1]})`}>
			<circle r={34} fill="#F4F7FA" stroke="#7E95AE" strokeWidth={4} />
			<g transform={`rotate(${ang})`}>
				<line x1={0} y1={0} x2={0} y2={-24} stroke="#0E2236" strokeWidth={5} strokeLinecap="round" />
			</g>
			<circle r={5} fill="#0E2236" />
		</g>
	);
};

const Tower: React.FC<{ok: boolean; failT: number}> = ({ok, failT}) => {
	const col = ok ? C.grid : C.alert;
	return (
		<g transform={`translate(${P.tower[0]},${P.tower[1]})`}>
			<path
				d="M-45,190 L-12,-110 L12,-110 L45,190 M-30,60 L30,60 M-20,-20 L20,-20 M-60,-80 L60,-80 M-50,-40 L50,-40 M-36,60 L22,-20 M36,60 L-22,-20"
				stroke={col}
				strokeWidth={6}
				fill="none"
				strokeLinejoin="round"
			/>
			{!ok && (
				<g opacity={failT} transform={`scale(${0.6 + failT * 0.4})`}>
					<circle r={52} fill={C.alert} />
					<path d="M-22,-22 L22,22 M22,-22 L-22,22" stroke="#fff" strokeWidth={10} strokeLinecap="round" />
				</g>
			)}
		</g>
	);
};

const Battery: React.FC<{show: number; f: number}> = ({show, f}) => {
	if (show <= 0.01) return null;
	const level = interpolate(Math.sin(f / 8), [-1, 1], [0.75, 0.95]);
	return (
		<g transform={`translate(${P.battery[0]},${P.battery[1]}) scale(${show})`}>
			<rect x={-60} y={-38} width={110} height={76} rx={12} fill="#24384F" stroke={C.ac} strokeWidth={5} />
			<rect x={52} y={-14} width={12} height={28} rx={3} fill={C.ac} />
			<rect x={-50} y={-28} width={90 * level} height={56} rx={6} fill={C.ac} />
		</g>
	);
};

// Onda CC → CA
const WaveBox: React.FC<{show: number; morph: number}> = ({show, morph}) => {
	if (show <= 0.01) return null;
	const W = 420;
	const pts: string[] = [];
	for (let x = 0; x <= W; x += 6) {
		const y = Math.sin((x / W) * Math.PI * 4) * 45 * morph;
		pts.push(`${x},${y}`);
	}
	const color = interpolateColors(morph, [0, 1], [C.dc, C.ac]);
	return (
		<g transform="translate(560,850)" opacity={show}>
			<rect x={-20} y={-90} width={W + 40} height={200} rx={20} fill="#0B1622" stroke={C.wire} strokeWidth={3} />
			<line x1={0} y1={0} x2={W} y2={0} stroke={C.wire} strokeWidth={2} strokeDasharray="6 8" />
			<polyline points={pts.join(' ')} fill="none" stroke={color} strokeWidth={8} strokeLinecap="round" />
			<text x={W / 2} y={85} textAnchor="middle" fontFamily={FONT} fontWeight={700} fontSize={30} fill={color}>
				{morph < 0.5 ? 'CC  (continua)' : 'CA  ·  60 Hz'}
			</text>
		</g>
	);
};

// ---------- Textos ----------
const Caption: React.FC<{
	from: number;
	to: number;
	kicker?: string;
	kickerColor?: string;
	title: string;
	sub?: string;
	big?: boolean;
	y?: number;
}> = ({from, to, kicker, kickerColor = C.sun, title, sub, big, y = 260}) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	if (f < from || f >= to) return null;
	const op = fadeWindow(f, from, to, 8);
	const s = spring({frame: f - from, fps, config: {damping: 16, mass: 0.6}});
	const ty = interpolate(s, [0, 1], [40, 0]);
	return (
		<div
			style={{
				position: 'absolute',
				top: y,
				left: 70,
				right: 70,
				opacity: op,
				transform: `translateY(${ty}px)`,
				fontFamily: FONT,
				color: C.text,
			}}
		>
			{kicker && (
				<div style={{fontSize: 34, fontWeight: 800, letterSpacing: 4, color: kickerColor, marginBottom: 18}}>
					{kicker}
				</div>
			)}
			<div style={{fontSize: big ? 92 : 64, fontWeight: 800, lineHeight: 1.12, letterSpacing: -1}}>{title}</div>
			{sub && (
				<div style={{fontSize: 36, fontWeight: 500, color: C.muted, marginTop: 22, lineHeight: 1.3}}>{sub}</div>
			)}
		</div>
	);
};

// ---------- Composición ----------
export const SolarRed: React.FC = () => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();

	// Noche
	const night = interpolate(f, [T.night, T.night + 20, T.blackoutScene - 15, T.blackoutScene], [0, 1, 1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const bg = interpolateColors(night, [0, 1], [C.bgDay, C.bgNight]);
	const sunY = interpolate(night, [0, 1], [P.sun[1], P.sun[1] + 160]);
	const sunOp = 1 - night;

	// Estado de la red
	const gridDown = inRange(f, T.hookB, T.panel) || f >= T.gridFail;
	const failStart = f >= T.gridFail ? T.gridFail : T.hookB;
	const failT = spring({frame: f - failStart, fps, config: {damping: 12}});

	// Inversor
	const invOn = !(inRange(f, T.hookB + 15, T.panel) || inRange(f, T.invOff, T.battery + 10));

	// Casa iluminada
	let lit = 1;
	if (gridDown) lit = 0;
	if (f >= T.battery) lit = interpolate(f, [T.battery + 10, T.battery + 25], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

	// Flujos
	const producing = sunOp > 0.5 && invOn;
	const showFlowHook = f < T.hookB + 15;
	const flowDC = producing && (showFlowHook || f >= T.panel) ? 1 : 0;
	const flowAC = producing && (showFlowHook || f >= T.inverter) ? 1 : f >= T.battery + 10 ? 1 : 0;
	const exporting = inRange(f, T.exportStart, T.night) || inRange(f, T.blackoutScene, T.gridFail);
	const importing = inRange(f, T.night + 10, T.blackoutScene - 10);
	const flowBat = f >= T.battery + 10 ? 1 : 0;

	// Resaltados por escena
	const hl = (a: number, b: number) => fadeWindow(f, a, b, 10);

	// Onda
	const waveShow = hl(T.inverter, T.house);
	const morph = interpolate(f, [T.inverter + 50, T.inverter + 110], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: Easing.inOut(Easing.cubic),
	});

	// Parpadeo al caer la red
	const flicker =
		inRange(f, T.hookB, T.hookB + 12) || inRange(f, T.gridFail, T.gridFail + 12)
			? (Math.floor(f / 2) % 2 === 0 ? 0.35 : 0)
			: 0;

	const batteryShow = spring({frame: f - T.battery, fps, config: {damping: 12}});

	return (
		<AbsoluteFill style={{backgroundColor: bg}}>
			<svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{position: 'absolute'}}>
				{/* estrellas de noche */}
				{night > 0 &&
					Array.from({length: 30}).map((_, i) => (
						<circle
							key={i}
							cx={(i * 137) % 1080}
							cy={700 + ((i * 89) % 380)}
							r={2 + (i % 3)}
							fill="#fff"
							opacity={night * (0.3 + ((i * 7) % 10) / 15)}
						/>
					))}

				<Sun y={sunY} opacity={sunOp} />
				<Photons opacity={sunOp * (f < T.hookB || f >= T.panel ? 1 : 0.6)} />

				{/* cables */}
				{[PATH_PANEL_INV, PATH_INV_HOUSE, PATH_HOUSE_GRID].map((p, i) => (
					<path key={i} d={toD(p)} stroke={C.wire} strokeWidth={10} fill="none" strokeLinejoin="round" />
				))}
				{f >= T.battery && (
					<path d={toD(PATH_BAT_HOUSE)} stroke={C.wire} strokeWidth={10} fill="none" opacity={batteryShow} />
				)}

				<Flow pts={PATH_PANEL_INV} color={C.dc} active={flowDC} />
				<Flow pts={PATH_INV_HOUSE} color={C.ac} active={flowAC} />
				<Flow pts={PATH_HOUSE_GRID} color={C.ac} active={exporting ? 1 : 0} />
				<Flow pts={PATH_HOUSE_GRID} color={C.grid} active={importing ? 1 : 0} reverse />
				<Flow pts={PATH_INV_HOUSE.slice(1)} color={C.grid} active={importing ? 1 : 0} reverse n={4} />
				<Flow pts={PATH_BAT_HOUSE} color={C.dc} active={flowBat} n={4} />

				<Panel />
				<Inverter on={invOn} off={invOn ? 1 : 0} />
				<House lit={lit} />
				<Meter dir={exporting ? -1 : importing ? 1 : 0} />
				<Tower ok={!gridDown} failT={failT} />
				<Battery show={batteryShow} f={f} />
				<WaveBox show={waveShow} morph={morph} />
				{f >= T.battery && (
					<g opacity={batteryShow}>
						<rect x={770} y={1322} width={40} height={36} fill={bg} />
						<line x1={770} y1={1340} x2={806} y2={1318} stroke={C.alert} strokeWidth={8} strokeLinecap="round" />
					</g>
				)}

				{/* resaltados */}
				<Glow at={P.panel} r={150} on={hl(T.panel, T.inverter)} color={C.dc} />
				<Glow at={P.inverter} r={125} on={hl(T.inverter, T.house) + hl(T.gridFail, T.end)} color={T.gridFail <= f ? C.alert : C.ac} />
				<Glow at={P.house} r={150} on={hl(T.house, T.exportStart)} color={C.ac} />
				<Glow at={P.meter} r={60} on={hl(T.exportStart, T.blackoutScene)} color={C.grid} />

				{/* etiquetas */}
				{[
					['Panel', P.panel[0], 1420],
					['Inversor', P.inverter[0], 1420],
					['Casa', P.house[0], 1420],
					['Red', P.tower[0], 1420],
				].map(([t, x, y]) => (
					<text
						key={t as string}
						x={x as number}
						y={y as number}
						textAnchor="middle"
						fontFamily={FONT}
						fontWeight={600}
						fontSize={28}
						fill={C.muted}
						opacity={f >= T.battery ? 0 : 1}
					>
						{t}
					</text>
				))}
				<text
					x={P.meter[0]}
					y={1285}
					textAnchor="middle"
					fontFamily={FONT}
					fontWeight={600}
					fontSize={24}
					fill={C.muted}
					opacity={hl(T.exportStart, T.blackoutScene)}
				>
					Medidor
				</text>
				{f >= T.battery && (
					<text
						x={P.battery[0]}
						y={1590}
						textAnchor="middle"
						fontFamily={FONT}
						fontWeight={700}
						fontSize={30}
						fill={C.ac}
						opacity={batteryShow}
					>
						Batería
					</text>
				)}

				{/* contador anti-isla */}
				{inRange(f, T.gridFail, T.invOff + 20) && (
					<text
						x={P.inverter[0]}
						y={1045}
						textAnchor="middle"
						fontFamily={FONT}
						fontWeight={800}
						fontSize={44}
						fill={C.alert}
					>
						{f < T.invOff ? `${((T.invOff - f) / fps).toFixed(1)} s` : 'Desconectado'}
					</text>
				)}
			</svg>

			{/* destello al caer la red */}
			<AbsoluteFill style={{backgroundColor: '#000', opacity: flicker}} />

			{/* textos */}
			<Caption from={0} to={T.hookB} title="Tienes paneles solares en el techo." />
			<Caption from={T.hookB} to={T.q} title="Hay sol. Pero se va la luz." kicker="APAGÓN" kickerColor={C.alert} />
			<Caption from={T.q} to={T.q + 35} title="¿Tu casa sigue con electricidad?" />
			<Caption
				from={T.q + 35}
				to={T.panel}
				title="No."
				big
				sub="Y está diseñado así a propósito. Te explico por qué."
			/>
			<Caption
				from={T.panel}
				to={T.inverter}
				kicker="1 · EL PANEL"
				kickerColor={C.dc}
				title="Convierte la luz del sol en corriente continua."
				sub="Efecto fotovoltaico: la luz mueve electrones en el silicio."
			/>
			<Caption
				from={T.inverter}
				to={T.house}
				kicker="2 · EL INVERSOR"
				kickerColor={C.ac}
				title="La transforma en corriente alterna."
				sub="Y la sincroniza con la red eléctrica."
				y={240}
			/>
			<Caption
				from={T.house}
				to={T.exportStart}
				kicker="3 · TU CASA"
				kickerColor={C.ac}
				title="Consume primero la energía de tus paneles."
			/>
			<Caption
				from={T.exportStart}
				to={T.night}
				kicker="4 · LA RED"
				kickerColor={C.grid}
				title="Lo que sobra se inyecta a la red."
				sub="El medidor registra en ambos sentidos. El crédito depende de la regulación de cada país."
			/>
			<Caption
				from={T.night}
				to={T.blackoutScene}
				kicker="DE NOCHE"
				kickerColor={C.grid}
				title="No hay sol: tomas energía de la red."
			/>
			<Caption
				from={T.blackoutScene}
				to={T.gridFail}
				kicker="5 · EL DATO CURIOSO"
				kickerColor={C.alert}
				title="¿Qué pasa si la red se cae?"
			/>
			<Caption
				from={T.gridFail}
				to={T.end}
				kicker="5 · EL DATO CURIOSO"
				kickerColor={C.alert}
				title="El inversor se desconecta en menos de 2 segundos."
				sub="Protección anti-isla: evita energizar la línea mientras los técnicos la reparan."
			/>
			<Caption
				from={T.end}
				to={1350}
				title="¿Quieres luz en un apagón?"
				sub="Necesitas baterías y un inversor híbrido."
			/>

			{/* firma */}
			<div
				style={{
					position: 'absolute',
					top: 120,
					left: 70,
					fontFamily: FONT,
					fontSize: 28,
					fontWeight: 600,
					color: C.muted,
					letterSpacing: 1,
				}}
			>
				@mildred.linkimer
			</div>
		</AbsoluteFill>
	);
};
