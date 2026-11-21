import React from 'react';
import {Composition} from 'remotion';
import {SolarRed} from './SolarRed';

export const Root: React.FC = () => (
	<Composition
		id="SolarRed"
		component={SolarRed}
		durationInFrames={1350}
		fps={30}
		width={1080}
		height={1920}
	/>
);
