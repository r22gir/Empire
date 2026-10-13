import manifest from '../../public/signin-bg/manifest.json';

export type SignInSlide = {
  src: string;
  alt: string;
  diagram?: string;
  caption?: string;
};

export type SignInBackgroundManifest = {
  intervalMs: number;
  slides: SignInSlide[];
};

export const SIGNIN_BACKGROUNDS: SignInBackgroundManifest = manifest;
