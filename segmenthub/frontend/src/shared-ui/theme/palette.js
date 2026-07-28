import { tokens } from './tokens';

export const palette = {
  primary: {
    main: tokens.brand.primary,
    dark: tokens.brand.primaryDark,
    light: tokens.brand.primaryAlt,
    contrastText: '#FFFFFF',
  },
  secondary: {
    main: tokens.neutral.gray70,
    contrastText: '#FFFFFF',
  },
  error: {
    main: tokens.feedback.error,
  },
  warning: {
    main: tokens.feedback.warning,
  },
  info: {
    main: tokens.feedback.info,
  },
  success: {
    main: tokens.feedback.success,
  },
  background: {
    default: tokens.surface.canvas,
    paper: tokens.surface.paper,
  },
  text: {
    primary: tokens.neutral.black,
    secondary: tokens.neutral.gray90,
  },
};
