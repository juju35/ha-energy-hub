// Energy Hub — sidebar panel. Draws everything itself (no Lovelace card): the illustrated banner, which folds into a
// sticky bar on scroll, and six tabs (Overview, Production, Batteries, Losses, Finances, Settings). The data comes from
// the integration's snapshot (websocket `energy_hub/subscribe`, pushed every 30 seconds).
const ENERGY_HUB_PANEL_VERSION = '1.4.0';

const EH_ICONS = {
  'bell-outline': 'M10 21H14C14 22.1 13.1 23 12 23S10 22.1 10 21M21 19V20H3V19L5 17V11C5 7.9 7 5.2 10 4.3V4C10 2.9 10.9 2 12 2S14 2.9 14 4V4.3C17 5.2 19 7.9 19 11V17L21 19M17 11C17 8.2 14.8 6 12 6S7 8.2 7 11V18H17V11Z',
  'alert-outline': 'M12,2L1,21H23M12,6L19.53,19H4.47M11,10V14H13V10M11,16V18H13V16',
  'arrow-left-right': 'M6.45,17.45L1,12L6.45,6.55L7.86,7.96L4.83,11H19.17L16.14,7.96L17.55,6.55L23,12L17.55,17.45L16.14,16.04L19.17,13H4.83L7.86,16.04L6.45,17.45Z',
  'battery-70': 'M16,10H8V6H16M16.67,4H15V2H9V4H7.33A1.33,1.33 0 0,0 6,5.33V20.67C6,21.4 6.6,22 7.33,22H16.67A1.33,1.33 0 0,0 18,20.67V5.33C18,4.6 17.4,4 16.67,4Z',
  'battery-charging': 'M16.67,4H15V2H9V4H7.33A1.33,1.33 0 0,0 6,5.33V20.66C6,21.4 6.6,22 7.33,22H16.66C17.4,22 18,21.4 18,20.67V5.33C18,4.6 17.4,4 16.67,4M11,20V14.5H9L13,7V12.5H15',
  'calendar-month': 'M9,10V12H7V10H9M13,10V12H11V10H13M17,10V12H15V10H17M19,3A2,2 0 0,1 21,5V19A2,2 0 0,1 19,21H5C3.89,21 3,20.1 3,19V5A2,2 0 0,1 5,3H6V1H8V3H16V1H18V3H19M19,19V8H5V19H19M9,14V16H7V14H9M13,14V16H11V14H13M17,14V16H15V14H17Z',
  'chart-line': 'M16,11.78L20.24,4.45L21.97,5.45L16.74,14.5L10.23,10.75L5.46,19H22V21H2V3H4V17.54L9.5,8L16,11.78Z',
  'check': 'M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z',
  'chevron-right': 'M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z',
  'cog-outline': 'M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8M12,10A2,2 0 0,0 10,12A2,2 0 0,0 12,14A2,2 0 0,0 14,12A2,2 0 0,0 12,10M10,22C9.75,22 9.54,21.82 9.5,21.58L9.13,18.93C8.5,18.68 7.96,18.34 7.44,17.94L4.95,18.95C4.73,19.03 4.46,18.95 4.34,18.73L2.34,15.27C2.21,15.05 2.27,14.78 2.46,14.63L4.57,12.97L4.5,12L4.57,11L2.46,9.37C2.27,9.22 2.21,8.95 2.34,8.73L4.34,5.27C4.46,5.05 4.73,4.96 4.95,5.05L7.44,6.05C7.96,5.66 8.5,5.32 9.13,5.07L9.5,2.42C9.54,2.18 9.75,2 10,2H14C14.25,2 14.46,2.18 14.5,2.42L14.87,5.07C15.5,5.32 16.04,5.66 16.56,6.05L19.05,5.05C19.27,4.96 19.54,5.05 19.66,5.27L21.66,8.73C21.79,8.95 21.73,9.22 21.54,9.37L19.43,11L19.5,12L19.43,13L21.54,14.63C21.73,14.78 21.79,15.05 21.66,15.27L19.66,18.73C19.54,18.95 19.27,19.04 19.05,18.95L16.56,17.95C16.04,18.34 15.5,18.68 14.87,18.93L14.5,21.58C14.46,21.82 14.25,22 14,22H10M11.25,4L10.88,6.61C9.68,6.86 8.62,7.5 7.85,8.39L5.44,7.35L4.69,8.65L6.8,10.2C6.4,11.37 6.4,12.64 6.8,13.8L4.68,15.36L5.43,16.66L7.86,15.62C8.63,16.5 9.68,17.14 10.87,17.38L11.24,20H12.76L13.13,17.39C14.32,17.14 15.37,16.5 16.14,15.62L18.57,16.66L19.32,15.36L17.2,13.81C17.6,12.64 17.6,11.37 17.2,10.2L19.31,8.65L18.56,7.35L16.15,8.39C15.38,7.5 14.32,6.86 13.12,6.62L12.75,4H11.25Z',
  'content-copy': 'M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z',
  'currency-eur': 'M15 18.5C12.5 18.5 10.32 17.08 9.24 15H15L16 13H8.58C8.53 12.67 8.5 12.34 8.5 12S8.53 11.33 8.58 11H15L16 9H9.24C10.32 6.92 12.5 5.5 15 5.5C16.61 5.5 18.09 6.09 19.23 7.07L21 5.3C19.41 3.87 17.3 3 15 3C11.08 3 7.76 5.5 6.5 9H3L2 11H6.06C6 11.33 6 11.66 6 12S6 12.67 6.06 13H3L2 15H6.5C7.76 18.5 11.08 21 15 21C17.31 21 19.41 20.13 21 18.7L19.22 16.93C18.09 17.91 16.62 18.5 15 18.5Z',
  'flag-outline': 'M12.36,6L12.76,8H18V14H14.64L14.24,12H7V6H12.36M14,4H5V21H7V14H12.6L13,16H20V6H14.4',
  'flash-outline': 'M7,2H17L13.5,9H17L10,22V14H7V2M9,4V12H12V14.66L14,11H10.24L13.76,4H9Z',
  'function-variant': 'M12.42,5.29C11.32,5.19 10.35,6 10.25,7.11L10,10H12.82V12H9.82L9.38,17.07C9.18,19.27 7.24,20.9 5.04,20.7C3.79,20.59 2.66,19.9 2,18.83L3.5,17.33C3.83,18.38 4.96,18.97 6,18.63C6.78,18.39 7.33,17.7 7.4,16.89L7.82,12H4.82V10H8L8.27,6.93C8.46,4.73 10.39,3.1 12.6,3.28C13.86,3.39 15,4.09 15.66,5.17L14.16,6.67C13.91,5.9 13.23,5.36 12.42,5.29M22,13.65L20.59,12.24L17.76,15.07L14.93,12.24L13.5,13.65L16.35,16.5L13.5,19.31L14.93,20.72L17.76,17.89L20.59,20.72L22,19.31L19.17,16.5L22,13.65Z',
  'gauge': 'M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12C20,14.4 19,16.5 17.3,18C15.9,16.7 14,16 12,16C10,16 8.2,16.7 6.7,18C5,16.5 4,14.4 4,12A8,8 0 0,1 12,4M14,5.89C13.62,5.9 13.26,6.15 13.1,6.54L11.81,9.77L11.71,10C11,10.13 10.41,10.6 10.14,11.26C9.73,12.29 10.23,13.45 11.26,13.86C12.29,14.27 13.45,13.77 13.86,12.74C14.12,12.08 14,11.32 13.57,10.76L13.67,10.5L14.96,7.29L14.97,7.26C15.17,6.75 14.92,6.17 14.41,5.96C14.28,5.91 14.15,5.89 14,5.89M10,6A1,1 0 0,0 9,7A1,1 0 0,0 10,8A1,1 0 0,0 11,7A1,1 0 0,0 10,6M7,9A1,1 0 0,0 6,10A1,1 0 0,0 7,11A1,1 0 0,0 8,10A1,1 0 0,0 7,9M17,9A1,1 0 0,0 16,10A1,1 0 0,0 17,11A1,1 0 0,0 18,10A1,1 0 0,0 17,9Z',
  'heart-pulse': 'M7.5,4A5.5,5.5 0 0,0 2,9.5C2,10 2.09,10.5 2.22,11H6.3L7.57,7.63C7.87,6.83 9.05,6.75 9.43,7.63L11.5,13L12.09,11.58C12.22,11.25 12.57,11 13,11H21.78C21.91,10.5 22,10 22,9.5A5.5,5.5 0 0,0 16.5,4C14.64,4 13,4.93 12,6.34C11,4.93 9.36,4 7.5,4V4M3,12.5A1,1 0 0,0 2,13.5A1,1 0 0,0 3,14.5H5.44L11,20C12,20.9 12,20.9 13,20L18.56,14.5H21A1,1 0 0,0 22,13.5A1,1 0 0,0 21,12.5H13.4L12.47,14.8C12.07,15.81 10.92,15.67 10.55,14.83L8.5,9.5L7.54,11.83C7.39,12.21 7.05,12.5 6.6,12.5H3Z',
  'home-lightning-bolt-outline': 'M5 20V12H2L12 3L22 12H19V20H5M12 5.69L7 10.19V18H17V10.19L12 5.69M11.5 18V14H9L12.5 7V11H15L11.5 18Z',
  'information-outline': 'M11,9H13V7H11M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M11,17H13V11H11V17Z',
  'layers-triple-outline': 'M12 16.54L19.37 10.8L21 12.07L12 19.07L3 12.07L4.62 10.81L12 16.54M12 14L3 7L12 0L21 7L12 14M12 2.53L6.26 7L12 11.47L17.74 7L12 2.53M12 21.47L19.37 15.73L21 17L12 24L3 17L4.62 15.74L12 21.47',
  'lightbulb-on-outline': 'M20,11H23V13H20V11M1,11H4V13H1V11M13,1V4H11V1H13M4.92,3.5L7.05,5.64L5.63,7.05L3.5,4.93L4.92,3.5M16.95,5.63L19.07,3.5L20.5,4.93L18.37,7.05L16.95,5.63M12,6A6,6 0 0,1 18,12C18,14.22 16.79,16.16 15,17.2V19A1,1 0 0,1 14,20H10A1,1 0 0,1 9,19V17.2C7.21,16.16 6,14.22 6,12A6,6 0 0,1 12,6M14,21V22A1,1 0 0,1 13,23H11A1,1 0 0,1 10,22V21H14M11,18H13V15.87C14.73,15.43 16,13.86 16,12A4,4 0 0,0 12,8A4,4 0 0,0 8,12C8,13.86 9.27,15.43 11,15.87V18Z',
  'menu': 'M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z',
  'minus': 'M19,13H5V11H19V13Z',
  'close': 'M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z',
  'piggy-bank-outline': 'M15 10C15 9.45 15.45 9 16 9C16.55 9 17 9.45 17 10S16.55 11 16 11 15 10.55 15 10M8 9H13V7H8V9M22 7.5V14.47L19.18 15.41L17.5 21H12V19H10V21H4.5C4.5 21 2 12.54 2 9.5S4.46 4 7.5 4H12.5C13.41 2.79 14.86 2 16.5 2C17.33 2 18 2.67 18 3.5C18 3.71 17.96 3.9 17.88 4.08C17.74 4.42 17.62 4.81 17.56 5.23L19.83 7.5H22M20 9.5H19L15.5 6C15.5 5.35 15.59 4.71 15.76 4.09C14.79 4.34 14 5.06 13.67 6H7.5C5.57 6 4 7.57 4 9.5C4 11.38 5.22 16.15 6 19H8V17H14V19H16L17.56 13.85L20 13.03V9.5Z',
  'power-plug-off-outline': 'M22.11 21.46L2.39 1.73L1.11 3L6.25 8.14C6.1 8.41 6 8.7 6 9V14.5L9.5 18V21H14.5V18L15.31 17.2L20.84 22.73L22.11 21.46M13.09 16.59L12.67 17H11.33L10.92 16.59L8 13.67V9.89L13.89 15.78L13.09 16.59M12.2 9L10.2 7H14V3H16V7C17 7 18 8 18 9V14.5L17.85 14.65L16 12.8V9.09C16 9.06 15.95 9 15.92 9H12.2M10 6.8L8 4.8V3H10V6.8Z',
  'refresh': 'M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z',
  'scale-balance': 'M12,3C10.73,3 9.6,3.8 9.18,5H3V7H4.95L2,14C1.53,16 3,17 5.5,17C8,17 9.56,16 9,14L6.05,7H9.17C9.5,7.85 10.15,8.5 11,8.83V20H2V22H22V20H13V8.82C13.85,8.5 14.5,7.85 14.82,7H17.95L15,14C14.53,16 16,17 18.5,17C21,17 22.56,16 22,14L19.05,7H21V5H14.83C14.4,3.8 13.27,3 12,3M12,5A1,1 0 0,1 13,6A1,1 0 0,1 12,7A1,1 0 0,1 11,6A1,1 0 0,1 12,5M5.5,10.25L7,14H4L5.5,10.25M18.5,10.25L20,14H17L18.5,10.25Z',
  'solar-panel': 'M4,2H20A2,2 0 0,1 22,4V14A2,2 0 0,1 20,16H15V20H18V22H13V16H11V22H6V20H9V16H4A2,2 0 0,1 2,14V4A2,2 0 0,1 4,2M4,4V8H11V4H4M4,14H11V10H4V14M20,14V10H13V14H20M20,4H13V8H20V4Z',
  'solar-power-variant': 'M3.33 16H11V13H4L3.33 16M13 16H20.67L20 13H13V16M21.11 18H13V22H22L21.11 18M2 22H11V18H2.89L2 22M11 8H13V11H11V8M15.76 7.21L17.18 5.79L19.3 7.91L17.89 9.33L15.76 7.21M4.71 7.91L6.83 5.79L8.24 7.21L6.12 9.33L4.71 7.91M3 2H6V4H3V2M18 2H21V4H18V2M12 7C14.76 7 17 4.76 17 2H7C7 4.76 9.24 7 12 7Z',
  'sync': 'M12,18A6,6 0 0,1 6,12C6,11 6.25,10.03 6.7,9.2L5.24,7.74C4.46,8.97 4,10.43 4,12A8,8 0 0,0 12,20V23L16,19L12,15M12,4V1L8,5L12,9V6A6,6 0 0,1 18,12C18,13 17.75,13.97 17.3,14.8L18.76,16.26C19.54,15.03 20,13.57 20,12A8,8 0 0,0 12,4Z',
  'target': 'M11,2V4.07C7.38,4.53 4.53,7.38 4.07,11H2V13H4.07C4.53,16.62 7.38,19.47 11,19.93V22H13V19.93C16.62,19.47 19.47,16.62 19.93,13H22V11H19.93C19.47,7.38 16.62,4.53 13,4.07V2M11,6.08V8H13V6.09C15.5,6.5 17.5,8.5 17.92,11H16V13H17.91C17.5,15.5 15.5,17.5 13,17.92V16H11V17.91C8.5,17.5 6.5,15.5 6.08,13H8V11H6.09C6.5,8.5 8.5,6.5 11,6.08M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11Z',
  'thermometer': 'M15 13V5A3 3 0 0 0 9 5V13A5 5 0 1 0 15 13M12 4A1 1 0 0 1 13 5V8H11V5A1 1 0 0 1 12 4Z',
  'timer-sand': 'M6,2H18V8H18V8L14,12L18,16V16H18V22H6V16H6V16L10,12L6,8V8H6V2M16,16.5L12,12.5L8,16.5V20H16V16.5M12,11.5L16,7.5V4H8V7.5L12,11.5M10,6H14V6.75L12,8.75L10,6.75V6Z',
  'transmission-tower': 'M8.28,5.45L6.5,4.55L7.76,2H16.23L17.5,4.55L15.72,5.44L15,4H9L8.28,5.45M18.62,8H14.09L13.3,5H10.7L9.91,8H5.38L4.1,10.55L5.89,11.44L6.62,10H17.38L18.1,11.45L19.89,10.56L18.62,8M17.77,22H15.7L15.46,21.1L12,15.9L8.53,21.1L8.3,22H6.23L9.12,11H11.19L10.83,12.35L12,14.1L13.16,12.35L12.81,11H14.88L17.77,22M11.4,15L10.5,13.65L9.32,18.13L11.4,15M14.68,18.12L13.5,13.64L12.6,15L14.68,18.12Z',
  'trending-down': 'M16,18L18.29,15.71L13.41,10.83L9.41,14.83L2,7.41L3.41,6L9.41,12L13.41,8L19.71,14.29L22,12V18H16Z',
  'view-dashboard-outline': 'M19,5V7H15V5H19M9,5V11H5V5H9M19,13V19H15V13H19M9,17V19H5V17H9M21,3H13V9H21V3M11,3H3V13H11V3M21,11H13V21H21V11M11,15H3V21H11V15Z',
  'water-off': 'M20.84 22.73L16.29 18.18C15.2 19.3 13.69 20 12 20C8.69 20 6 17.31 6 14C6 12.67 6.67 11.03 7.55 9.44L1.11 3L2.39 1.73L22.11 21.46L20.84 22.73M18 14C18 10 12 3.25 12 3.25S10.84 4.55 9.55 6.35L17.95 14.75C18 14.5 18 14.25 18 14Z',
  'weather-cloudy-alert': 'M6,19A5,5 0 0,1 1,14A5,5 0 0,1 6,9C7,6.65 9.3,5 12,5C15.43,5 18.24,7.66 18.5,11.03L19,11A4,4 0 0,1 23,15A4,4 0 0,1 19,19H6M19,13H17V12A5,5 0 0,0 12,7C9.5,7 7.45,8.82 7.06,11.19C6.73,11.07 6.37,11 6,11A3,3 0 0,0 3,14A3,3 0 0,0 6,17H19A2,2 0 0,0 21,15A2,2 0 0,0 19,13M13,12H11V8H13V12M13,16H11V14H13',
  'white-balance-sunny': 'M3.55 19.09L4.96 20.5L6.76 18.71L5.34 17.29M12 6C8.69 6 6 8.69 6 12S8.69 18 12 18 18 15.31 18 12C18 8.68 15.31 6 12 6M20 13H23V11H20M17.24 18.71L19.04 20.5L20.45 19.09L18.66 17.29M20.45 5L19.04 3.6L17.24 5.39L18.66 6.81M13 1H11V4H13M6.76 5.39L4.96 3.6L3.55 5L5.34 6.81L6.76 5.39M1 13H4V11H1M13 20H11V23H13',
};

const EH_TABS = [
  ['overview', 'view-dashboard-outline'],
  ['production', 'white-balance-sunny'],
  ['batteries', 'battery-70'],
  ['losses', 'trending-down'],
  ['finances', 'currency-eur'],
  ['settings', 'cog-outline'],
];

// The other languages are files next to the panel (frontend/i18n/<lang>.json), fetched when Home Assistant uses one.
const EH_LANGS = ['fr', 'de', 'es', 'it', 'nl', 'pt', 'pl', 'sr', 'sr-Latn', 'ro', 'da', 'sv', 'bg', 'ru', 'uk', 'hu', 'sk', 'cs', 'sl', 'lv', 'el'];

const EH_I18N = {
  en: {
    title: 'Energy',
    tabs: { overview: 'Overview', production: 'Production', batteries: 'Batteries', losses: 'Losses', finances: 'Finances', settings: 'Settings' },
    demo: 'Demo',
    loading: 'Loading Energy Hub…',
    not_loaded: 'Energy Hub is not loaded.',
    producing: 'Producing {v}',
    battery_pill: 'Battery {v}',
    night: 'Night',
    alert_pill: '{n} alert(s)',
    subline_day: '{sc} self-consumed · battery {soc}',
    subline_night: 'Home {load} · autonomy {aut}',
    kwp: '{v} kWp',
    solar: 'Solar',
    home: 'Home',
    battery: 'Battery',
    batteries_n: '{n} batteries',
    grid: 'Grid',
    importing: 'Importing',
    exporting: 'Exporting',
    idle: 'Idle',
    charging: 'Charging',
    discharging: 'Discharging',
    full: 'Full',
    of_peak: '{v} of peak',
    solar_share: '{v} solar',
    full_at: 'full at {v}',
    self_consumption: 'Self-consumption',
    self_sufficiency: 'Self-sufficiency',
    saved: 'Saved',
    losses: 'Losses',
    vs_yesterday: '{v} vs yesterday',
    pts: 'pts',
    resale: 'resale {v}',
    of_day: '{v} · {p} of the day',
    production: 'Production',
    forecast: 'Forecast',
    consumption: 'Consumption',
    battery_pct: 'Battery %',
    clipping: 'Clipping',
    produced_of: '{a} produced · {b} expected',
    hover_hint: 'Hover the curve for details',
    inverter_max: 'Inverter max {v}',
    clipped: 'Clipped {v}',
    alerts: {
      clipping: ['Clipping {from} – {to}', '{kwh} lost · {days} day(s) this week'],
      string_lagging: ['{name} lagging', '{pct} vs its peers for {days} days'],
      shading: ['Shading {unit}', 'Every clear day {from} – {to} · {kwh}/day'],
      soiling: ['Soiling', '{pct} lost: a cleaning may pay'],
      cell_drift: ['{battery}: cell {cell}', 'Spread threshold in {days} days'],
      battery_exchange: ['Battery to battery', '{kw} sent from one battery into another'],
      stale: ['Source not updating', '{entities}'],
    },
    yield: 'Specific yield',
    pr: 'Performance index',
    pr_range: 'healthy range {v}',
    peak_day: 'Peak of the day',
    reached_limit: 'inverter limit reached',
    this_month: 'This month',
    of_expected: '{v} of expected',
    roof: 'Roof · yield per panel',
    roof_hint: '% of the best panel · today',
    strings: 'Strings',
    pr_30: 'Performance index · 30 days',
    rain: 'drops = rain',
    months_12: '12 months',
    expected_line: 'line = expected',
    fleet: 'Fleet',
    net_power: 'Net power',
    n_charging: '{c} charging · {d} discharging',
    autonomy: 'Autonomy',
    autonomy_sub: 'at {v} · reserves kept',
    exchange: 'Internal exchange',
    to_avoid: 'to avoid',
    none: 'none',
    all: 'All',
    compare: 'Compare',
    health: 'State of health',
    cycles: 'Cycles',
    rte: 'Round-trip efficiency',
    temperature: 'Temperature',
    estimated: 'estimated',
    measured: '{a} / {b} measured',
    cells: 'Cells',
    voltage: 'Voltage',
    deviation: 'Deviation',
    spread: 'Spread',
    min: 'Min',
    max: 'Max',
    threshold_in: 'threshold {t} in {d} days',
    stable: 'stable',
    no_cells: 'This battery does not report its cells.',
    capacity_share: 'Capacity share',
    lost_today: 'Lost today',
    this_month_lost: 'This month',
    availability: 'Availability',
    main_cause: 'Main cause',
    cascade: 'From potential to produced',
    axis_cut: 'Axis cut to make the losses readable',
    heatmap: 'Clipping · 30 days × hour',
    causes_month: 'Causes · this month',
    causes: { clipping: 'Clipping', shading: 'Shading', soiling: 'Soiling', limitation: 'Export limit', unavailability: 'Unavailability' },
    causes_short: { potential: 'Potential', clipping: 'Clipping', shading: 'Shading', soiling: 'Soiling', limitation: 'Export', unavailability: 'Offline', produced: 'Produced' },
    potential: 'Potential',
    produced: 'Produced',
    events: 'Events',
    no_event: 'No loss detected.',
    learning: 'learning · {d}/{n} days',
    soiling_trend: 'Soiling',
    degradation: 'Degradation',
    per_year: '{v}/year',
    amortised: 'paid back',
    gained_since: 'Gained since commissioning',
    of_net_cost: 'of {v} net cost',
    break_even: 'Break-even',
    in_years: 'in {v} years',
    gain_20: 'Net gain over 20 years',
    projection: 'Projection',
    price_rise: 'Price rise',
    per_year_short: '{v} %/year',
    net_cost: 'net cost {v}',
    inverter: 'inverter',
    gains_month: 'Gains per month',
    gains_from: 'Where the gains come from',
    direct: 'Direct self-consumption',
    battery_restored: 'Battery restored',
    export: 'Feed-in',
    no_cost: 'Set `installation: cost:` in YAML to see the payback.',
    sources: 'Sources',
    capabilities: { provided: 'provided', estimated: 'estimated by the hub', absent: 'not available' },
    yaml: 'YAML',
    copied: 'Copied',
    excluded: 'Excluded',
    excluded_reason: { ignore: 'ignored in YAML', double_count: 'already counted by the inverter (double count)' },
    health_title: 'Configuration',
    checks: {
      pv: 'Production detected',
      grid: 'Grid meter',
      battery: 'Batteries',
      forecast: 'Forecast',
      planes: 'Panel orientation',
      tariff: 'Tariff and installation cost',
    },
    check_missing: 'missing',
    kwp_estimated: 'kWp estimated from the peaks: set `planes:` in YAML',
    active: 'active',
    active_n: '{n} active',
    no_notify: 'none',
    detected: 'detected',
    inactive: 'inactive',
    after_years: 'after {v} years',
    alert_rules: 'Alert rules',
    alerts_label: 'Alerts',
    azimuth: 'Azimuth',
    balancing: 'Balancing',
    bill_hint: 'With solar: grid purchases at {i}/kWh minus feed-in at {e}/kWh. Without: the whole consumption bought.',
    bill_title: 'Bill with and without solar',
    capacity: 'Capacity',
    commissioned: 'Commissioned',
    computed: 'computed',
    copy_yaml: 'Copy YAML',
    correlation: 'charges follow each other (r = {v})',
    cost: 'Installation cost',
    credit: 'credit',
    days_30: '30 days',
    diag_drift: 'Drifts {v} mV a day against the others: balancing or a check of this cell may be needed.',
    diag_stable: 'Follows the other cells: nothing to do.',
    drifting: 'Drifting',
    event_name: 'Event',
    export_limit: 'Export limit',
    export_price: 'Feed-in price',
    frequency: 'Frequency',
    gains_calendar: 'Gains calendar',
    gaps: 'gaps {v}',
    high: 'high',
    home_computed: 'No home consumption sensor: computed from production, grid and batteries.',
    import_price: 'Purchase price',
    in_days: 'in {d} days',
    installation_box: 'Installation',
    inverter_cap: 'Inverter',
    inverter_max_short: 'Inverter maximum',
    inverter_replacement: 'Inverter replacement',
    last_seen: 'last value {v} ago',
    learning_short: 'Not enough data yet.',
    limit_kw: 'limit {v}',
    low: 'low',
    measured_short: 'measured',
    modules: 'Modules',
    modules_x_cells: '{m} modules × {c} cells',
    n_cells: '{n} cells',
    n_days: '{n} days',
    one_day: '1 day',
    net_cost_label: 'Net cost',
    no: 'no',
    notifications: 'Notifications',
    notify_target: 'Notify action',
    now_short: 'now',
    of_threshold: 'threshold {t}',
    once_a_day: 'once a day per alert',
    open: 'Open',
    panels: 'panels',
    per_day: '{v} a day',
    plane_n: 'Plane {n}',
    planes: 'Panels',
    power: 'Power',
    projection_dashed: 'dashed: projection',
    quality_24h: 'Data quality · 24 h',
    quality_hint: 'green: value read · red: missing',
    reserve: 'reserve {v}',
    saved_amount: '{v} saved',
    schematic: 'DC / AC layout',
    schematic_click: 'Click an element to see its capabilities and the entities used.',
    schematic_hint: 'click an element',
    soc: 'State of charge',
    soc_today: 'Charge · today',
    soh_3y: 'State of health · 3 years',
    spread_trend: 'Cell spread · trend',
    subsidy: 'Subsidy',
    suggestions: 'Suggestions',
    tariff_box: 'Tariff',
    threshold: 'threshold',
    tilt: 'Tilt',
    today: 'today',
    weeks_6: '6 weeks',
    with_solar: 'With solar',
    without_solar: 'Without solar',
    yaml_detected: 'equivalent to the detection',
    yaml_in_use: 'configuration.yaml in use',
    yaml_wins: 'Edit in configuration.yaml: the energy_hub: block wins over the detection.',
    yes: 'yes',
    periods: { today: 'Today', '7d': '7 d', '30d': '30 d', '12m': '12 mo' },
    coupling: { dc: 'DC-coupled', ac: 'AC-coupled' },
    status: { recurring: 'Recurring', watch: 'To watch', resolved: 'Resolved' },
    event: {
      clipping: 'Clipping',
      unavailability: 'Production unavailable',
      shading: 'Shading {unit} · {from} – {to}',
      string_lagging: '{name} lagging',
      soiling: 'Soiling',
      cell_drift: '{battery}: cell {cell} drifting',
    },
    subtabs: { sources: 'Sources', installation: 'Installation', tariffs: 'Tariffs', alerts: 'Alerts', yaml: 'YAML' },
    source_role: { pv: 'Production', storage: 'Storage', meter: 'Grid meter', forecast: 'Forecast', tariff: 'Tariff', weather: 'Weather', prefs: 'Energy dashboard' },
    suggest: {
      attach_bms: 'Attach {bms} to the {battery} battery',
      planes: 'Give the panels’ orientation (kWp, tilt, azimuth)',
      capacity: 'Give the capacity of {battery}',
      forecast: 'Add a production forecast',
    },
    cap: {
      strings: 'strings',
      optimizers: 'optimizers',
      microinverters: 'micro-inverters',
      pmax: 'inverter maximum',
      export_limit: 'export limit',
      soc: 'charge',
      power: 'power',
      soh: 'health',
      cycles: 'cycles',
      modules: 'modules',
      cells: 'cells',
      forecast: 'forecast',
      tempo: 'tariff colour',
      tariff: 'tariff',
      irradiance: 'irradiance',
      clouds: 'cloud cover',
    },
    role: {
      pv_power: 'Solar power',
      pv_energy: 'Solar energy',
      grid_power: 'Grid power',
      grid_import_energy: 'Grid import',
      grid_export_energy: 'Grid export',
      load_power: 'Home power',
      forecast_power: 'Forecast power',
      forecast_energy_today: 'Forecast today',
      irradiance: 'Irradiance',
      weather: 'Weather',
      tariff_price: 'Price of the kWh',
      tariff_color: 'Day colour',
    },
    alert_kind: {
      clipping: 'Clipping',
      string_lagging: 'String or panel lagging',
      shading: 'Recurring shading',
      soiling: 'Soiling',
      cell_drift: 'Cell drift',
      battery_exchange: 'Battery to battery',
      stale: 'Source not updating',
    },
    alert_rule: {
      clipping: 'more than 0.3 kWh clipped in the day',
      string_lagging: 'under 90 % of its peers for 3 days',
      shading: 'the same dip on 10 clear days or more',
      soiling: 'more than 3 % lost to soiling',
      cell_drift: 'cell spread reaching 50 mV within 14 days',
      battery_exchange: 'more than 0.1 kW sent from one battery into another',
      stale: 'an entity in use unavailable',
    },
    beta: 'beta',
    comparator: 'Offer comparator',
    comparator_hint: '12 months · {v} drawn',
    comparator_learning: 'The comparator needs {n} days of grid readings ({d} so far).',
    offer: 'Offer',
    avg_price: 'Average kWh',
    subscription: 'Subscription',
    total_year: 'Per year',
    your_contract: 'your contract',
    regulated: 'regulated',
    market: 'market',
    custom_offer: 'yours',
    best_saving: 'Switching to {name} would save about {v} a year.',
    best_is_current: 'Your contract is the cheapest for your consumption.',
    no_contract: 'Contract unknown: set tariff: contract: in YAML, or install Tarif EDF, to see the difference.',
    scaled: 'Based on {n} days of readings, scaled to a year.',
    colors_estimated: '{n} days priced at the season’s mix of Tempo or Zen Flex days (colour not recorded).',
    grid_info: 'EDF grid of {d}, VAT included. Market offers are references: check them against your contract.',
    grid_stale: 'The embedded grid is more than 7 months old: a revision may have come since.',
    contract_box: 'Contract',
    contract: 'Contract',
    subscribed_power: 'Subscribed power',
    offpeak_hours: 'Off-peak hours',
    price_now: 'Price now',
    price_entity: 'Price entity',
    color_entity: 'Day colour entity',
    assumed: 'by default',
    reference: 'Production reference',
    contract_source: { tarif_edf: 'Tarif EDF', yaml: 'YAML' },
    reference_kind: { measured: 'Measured irradiance', forecast: 'Solar forecast', weather: 'Weather cloud cover', clearsky: 'Clear sky' },
    reference_hint: {
      measured: 'clear sky scaled by the measured irradiance (IEC 61724-1)',
      forecast: 'from the forecast integration',
      weather: 'clear sky × (1 − 0.75 N^3.4), N the cloud cover',
      clearsky: 'no irradiance sensor, forecast or weather entity found',
    },
  },
};

const EH_AMBER = '#BA7517';
const EH_GREEN = '#3B6D11';
const EH_TEAL = '#1D9E75';
const EH_BLUE = '#378ADD';
const EH_RED = '#E24B4A';
const EH_VIOLET = '#7F77DD';

function ehEsc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

// Round axis ticks under ``max``: steps of 1, 2 or 5 × 10^n, about five of them
function ehTicks(max) {
  const raw = max / 5;
  const mag = 10 ** Math.floor(Math.log10(raw || 1));
  const step = [1, 2, 5, 10].map((k) => k * mag).find((k) => k >= raw) || mag;
  const out = [];
  for (let v = 0; v <= max + 1e-9; v += step) out.push(Math.round(v * 1000) / 1000);
  return out;
}

function ehIcon(name, size = 18) {
  const path = EH_ICONS[name] || EH_ICONS['information-outline'];
  return `<svg class="ic" width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="${path}"/></svg>`;
}

class EnergyHubPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._data = null;
    this._settings = null;
    this._tab = new URLSearchParams(location.search).get('tab') || 'overview';
    this._battery = 'all';
    this._cellMetric = 'deviation';
    this._cell = null;
    this._rate = 3;
    this._period = 'today';
    this._sub = 'sources';
    this._node = null;
    this._snips = [];
    this._collapsed = false;
    this._error = null;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    this._loadLang();
    if (first) this._connect();
  }

  get hass() {
    return this._hass;
  }

  set narrow(v) {
    this._narrow = v;
  }

  connectedCallback() {
    if (!this.shadowRoot.innerHTML) this._render();
  }

  disconnectedCallback() {
    this._unsub?.then((u) => u()).catch(() => {});
    this._unsub = null;
  }

  async _connect() {
    try {
      this._unsub = this._hass.connection.subscribeMessage(
        (data) => {
          this._data = data;
          this._render();
        },
        { type: 'energy_hub/subscribe' },
      );
      await this._unsub;
      this._settings = await this._hass.callWS({ type: 'energy_hub/settings' });
      this._render();
    } catch (err) {
      this._error = err?.message || String(err);
      this._render();
    }
  }

  // ---------- helpers
  get _lang() {
    const full = this._hass?.locale?.language || this._hass?.language || 'en';
    if (EH_LANGS.includes(full)) return full;
    const base = full.split('-')[0];
    return EH_LANGS.includes(base) ? base : 'en';
  }

  async _loadLang() {
    const lang = this._lang;
    if (lang === 'en' || EH_I18N[lang] || this._loading === lang) return;
    this._loading = lang;
    try {
      const res = await fetch(`/energy_hub_static/i18n/${lang}.json?v=${ENERGY_HUB_PANEL_VERSION}`);
      if (res.ok) {
        EH_I18N[lang] = await res.json();
        this._render();
      }
    } catch (_err) {
      // English stays
    }
    this._loading = null;
  }

  get _locale() {
    return this._hass?.locale?.language || this._hass?.language || 'en';
  }

  _t(path, params = {}, fallback = null) {
    const get = (dict) => path.split('.').reduce((o, k) => (o == null ? o : o[k]), dict);
    let s = get(EH_I18N[this._lang]) ?? get(EH_I18N.en) ?? fallback ?? path;
    if (typeof s !== 'string') return s;
    for (const [k, v] of Object.entries(params)) s = s.replaceAll(`{${k}}`, v);
    return s;
  }

  _num(v, d = 1) {
    if (v == null || Number.isNaN(v)) return '–';
    return new Intl.NumberFormat(this._hass?.locale?.language || 'en', { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
  }

  _kw(v) {
    return v == null ? '–' : `${this._num(Math.abs(v), Math.abs(v) < 10 ? 1 : 0)} kW`;
  }

  _kwh(v) {
    return v == null ? '–' : `${this._num(v, v < 10 ? 1 : 0)} kWh`;
  }

  _pct(v, d = 0) {
    return v == null ? '–' : `${this._num(v * 100, d)} %`;
  }

  _eur(v, d = 2) {
    if (v == null) return '–';
    return new Intl.NumberFormat(this._hass?.locale?.language || 'en', { style: 'currency', currency: this._data?.currency || 'EUR', minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
  }

  _hm(minute) {
    const h = Math.floor(minute / 60);
    const m = Math.round(minute % 60);
    return this._lang === 'fr' ? `${h} h ${String(m).padStart(2, '0')}` : `${h}:${String(m).padStart(2, '0')}`;
  }

  _time(ts) {
    const d = new Date(ts * 1000);
    return this._hm(d.getHours() * 60 + d.getMinutes());
  }

  get _dark() {
    return !!this._hass?.themes?.darkMode;
  }

  _setTab(tab) {
    this._tab = tab;
    const url = new URL(location.href);
    url.searchParams.set('tab', tab);
    history.replaceState(history.state, '', url);
    this._render();
    this.shadowRoot.querySelector('.scroll')?.scrollTo({ top: 0 });
  }

  // ---------- status
  _status() {
    const d = this._data;
    const night = !d.live.pv_kw || d.live.pv_kw < 0.02;
    const alerts = d.alerts.filter((a) => a.severity === 'error').length;
    const fleet = d.batteries.fleet;
    if (alerts) return { kind: 'alert', short: `! ${d.alerts.length}`, pill: this._t('alert_pill', { n: d.alerts.length }), bg: '#F7C1C1', fg: '#791F1F', icBg: '#F7C1C1', icFg: '#791F1F' };
    if (night && fleet?.soc != null) return { kind: 'night', short: this._pct(fleet.soc / 100), pill: this._t('battery_pill', { v: this._pct(fleet.soc / 100) }), bg: '#9FE1CB', fg: '#085041', icBg: '#9FE1CB', icFg: '#085041' };
    if (night) return { kind: 'night', short: '☾', pill: this._t('night'), bg: '#D3D1C7', fg: '#444441', icBg: '#D3D1C7', icFg: '#444441' };
    return { kind: 'day', short: this._kw(d.live.pv_kw), pill: this._t('producing', { v: this._kw(d.live.pv_kw) }), bg: '#C0DD97', fg: '#27500A', icBg: '#FAC775', icFg: '#633806' };
  }

  // ---------- banner
  _scene(st) {
    const d = this._data;
    const night = this._dark;
    const { sky, ground, cloudy } = this._sky();
    const now = new Date(d.generated);
    const minutes = now.getHours() * 60 + now.getMinutes();
    const frac = Math.min(Math.max((minutes - 360) / (22 * 60 - 360), 0), 1);
    const sx = 330 + frac * 350;
    const sy = 92 - Math.sin(frac * Math.PI) * 74;
    const fleet = d.batteries.fleet;
    const soc = fleet?.soc ?? 0;
    const pv = d.live.pv_kw || 0;
    const grid = d.live.grid_kw || 0;
    const batt = d.live.battery_kw || 0;
    const pylon = night ? '#6E7896' : '#8D8A80';
    const dots = (path, color, n, dur, r) => {
      let o = '';
      for (let i = 0; i < n; i++) o += `<circle r="${r}" fill="${color}"><animateMotion dur="${dur}s" begin="-${((i * dur) / n).toFixed(2)}s" repeatCount="indefinite" path="${path}"/></circle>`;
      return o;
    };
    let o = `<svg class="scene" viewBox="0 0 680 90" preserveAspectRatio="xMaxYMax meet" aria-hidden="true"><rect width="680" height="90" fill="${sky}"/>`;
    if (night) {
      for (let i = 0; i < 20; i++) o += `<circle cx="${360 + ((i * 97) % 310)}" cy="${6 + ((i * 53) % 40)}" r="${i % 3 ? 0.8 : 1.2}" fill="#F1EFE8" opacity=".7"><animate attributeName="opacity" values=".2;.9;.2" dur="${2 + (i % 3)}s" repeatCount="indefinite"/></circle>`;
      o += `<circle cx="585" cy="22" r="10" fill="#F1EFE8"/><circle cx="590" cy="19" r="9" fill="${sky}"/>`;
    } else {
      o += `<path d="M330 92 Q505 -40 680 92" fill="none" stroke="#E2C489" stroke-dasharray="2 4"/>`;
      if (pv > 0.02) o += `<g transform="translate(${sx.toFixed(0)} ${sy.toFixed(0)})"><circle r="22" fill="#F5B84A" fill-opacity=".18"/><circle r="11" fill="#F5B84A"/></g>`;
      if (cloudy) for (let c = 0; c < 3; c++) o += `<g fill="#fff" fill-opacity=".92"><animateTransform attributeName="transform" type="translate" values="0 0;14 0;0 0" dur="${9 + c * 3}s" repeatCount="indefinite"/><ellipse cx="${430 + c * 70}" cy="${20 + (c % 2) * 10}" rx="26" ry="8"/><ellipse cx="${442 + c * 70}" cy="${14 + (c % 2) * 10}" rx="15" ry="9"/></g>`;
    }
    o += `<path d="M300 84 C380 66 430 70 470 76 C520 62 600 66 680 74 L680 84 Z" fill="${night ? '#26324F' : cloudy ? '#D3D9D2' : '#EDD9AE'}"/>`;
    o += `<polygon points="456,52 516,26 576,52" fill="${night ? '#5A3328' : '#B4553A'}"/><polygon points="474,46 510,30 528,38 492,54" fill="${night ? '#1B2A45' : '#2F4A70'}"/>`;
    o += `<g stroke="${night ? '#33456A' : '#FBEFD6'}" stroke-width="1.1"><line x1="486" y1="40" x2="504" y2="48"/><line x1="498" y1="35" x2="516" y2="43"/><line x1="483" y1="50" x2="519" y2="34"/></g>`;
    if (pv > 0.3 && !night) o += `<clipPath id="ehcp"><polygon points="474,46 510,30 528,38 492,54"/></clipPath><g clip-path="url(#ehcp)"><rect x="440" y="20" width="8" height="50" fill="#fff" fill-opacity=".55" transform="rotate(25 480 40)"><animate attributeName="x" values="440;560" dur="3.2s" repeatCount="indefinite"/></rect></g>`;
    if (st.kind === 'alert') o += `<circle cx="530" cy="30" r="7" fill="${EH_RED}"/><text x="530" y="33.5" text-anchor="middle" font-size="10" font-weight="500" fill="#fff">!</text>`;
    const win = night ? '#F5C451' : '#F7D98F';
    o += `<rect x="464" y="52" width="104" height="32" fill="${night ? '#3A4560' : '#EFE5CF'}"/><rect x="506" y="62" width="16" height="22" fill="${night ? '#2A3350' : '#A88F64'}"/><rect x="476" y="60" width="18" height="12" rx="1" fill="${win}"/><rect x="536" y="60" width="18" height="12" rx="1" fill="${win}"/>`;
    if (fleet) {
      const bh = Math.round((16 * soc) / 100);
      o += `<rect x="575" y="58" width="16" height="24" rx="3" fill="#5F5E5A"/><rect x="579" y="${80 - bh}" width="8" height="${bh}" rx="1" fill="${EH_TEAL}"/><rect x="580" y="55" width="6" height="3" rx="1" fill="#5F5E5A"/>`;
      if (Math.abs(batt) > 0.05) o += `<rect x="579" y="61" width="8" height="2" rx="1" fill="${EH_TEAL}"><animate attributeName="opacity" values="1;.2;1" dur="1.4s" repeatCount="indefinite"/></rect>`;
    }
    o += `<g stroke="${pylon}" stroke-width="1.5" fill="none" stroke-linejoin="round"><path d="M632 84 L642 34 L652 84"/><line x1="635" y1="68" x2="649" y2="68"/><line x1="638" y1="52" x2="646" y2="52"/><line x1="628" y1="40" x2="656" y2="40"/></g>`;
    const wire = 'M568 64 Q600 46 628 40';
    o += `<path d="${wire}" fill="none" stroke="${pylon}" stroke-width=".9"/>`;
    if (grid < -0.05) o += dots(wire, EH_BLUE, 3, 1.8, 2.2);
    if (grid > 0.05) o += dots('M628 40 Q600 46 568 64', '#888780', 3, 2, 2.2);
    if (pv > 0.05 && batt > 0.05) o += dots('M520 46 L583 58', '#EF9F27', 2, 1.4, 1.8);
    if (batt < -0.05) o += dots('M583 70 L568 70', '#5DCAA5', 2, 1.2, 1.8);
    o += `<rect x="0" y="84" width="680" height="6" fill="${ground}"/></svg>`;
    return o;
  }

  _sky() {
    const L = this._data.live;
    if (this._dark) return { sky: '#1C2740', ground: '#2E3A55', cloudy: false };
    const cloudy = L.expected_kw != null && L.pv_kw != null && L.expected_kw > 0.3 && L.pv_kw / L.expected_kw < 0.5;
    return cloudy ? { sky: '#E8ECEF', ground: '#B8B6A8', cloudy } : { sky: '#FBEFD6', ground: '#C9B28A', cloudy };
  }

  _header() {
    const d = this._data;
    const st = this._status();
    const fleet = d.batteries.fleet;
    const night = !d.live.pv_kw || d.live.pv_kw < 0.02;
    const sub = night
      ? this._t('subline_night', { load: this._kw(d.live.load_kw), aut: d.batteries.autonomy_h != null ? `${this._num(d.batteries.autonomy_h, 0)} h` : '–' })
      : this._t('subline_day', { sc: this._pct(d.today.self_consumption), soc: fleet?.soc != null ? this._pct(fleet.soc / 100) : '–' });
    const textColor = this._dark ? '#F1EFE8' : '#412402';
    const subColor = this._dark ? '#B4B2A9' : '#854F0B';
    const tabs = EH_TABS.map(([key, icon]) => {
      const dot = key === 'losses' && d.alerts.length && this._tab !== 'losses' ? '<span class="dot"></span>' : '';
      return `<button class="tabpill ${this._tab === key ? 'on' : ''}" data-tab="${key}" title="${ehEsc(this._t(`tabs.${key}`))}" aria-label="${ehEsc(this._t(`tabs.${key}`))}">${ehIcon(icon, 17)}${dot}</button>`;
    }).join('');
    return `
      <header class="banner ${this._collapsed ? 'collapsed' : ''}" style="--txt:${textColor};--sub:${subColor};--sky:${this._sky().sky};--ground:${this._sky().ground};--btn:${this._dark ? 'rgba(255,255,255,.14)' : 'rgba(255,255,255,.6)'}">
        ${this._scene(st)}
        <div class="bar">
          <button class="round menu" data-action="menu" aria-label="Menu">${ehIcon('menu', 20)}</button>
          <div class="badge" style="background:${st.icBg};color:${st.icFg}">${ehIcon('solar-power-variant', 22)}</div>
          <div class="titles">
            <div class="title"><span class="tname">${ehEsc(this._t('title'))}</span><span class="pill" style="background:${st.bg};color:${st.fg}"><span class="long">${ehEsc(st.pill)}</span><span class="short">${ehEsc(st.short)}</span></span>${d.demo ? `<span class="pill demo">${ehEsc(this._t('demo'))}</span>` : ''}</div>
            <div class="sub">${ehEsc(sub)} · ${ehEsc(this._t('kwp', { v: this._num(d.kwp, 1) }))}</div>
          </div>
          <div class="tabpills">${tabs}</div>
          <button class="round bell" data-tab="losses" aria-label="${ehEsc(this._t('alerts_label'))}">${ehIcon('bell-outline', 18)}${d.alerts.length ? `<span class="count">${d.alerts.length}</span>` : ''}</button>
          <button class="round refresh" data-action="refresh" aria-label="Refresh">${ehIcon('refresh', 18)}</button>
        </div>
      </header>
      <nav class="tabs">${EH_TABS.map(([key]) => `<button class="tab ${this._tab === key ? 'on' : ''}" data-tab="${key}">${ehEsc(this._t(`tabs.${key}`))}${key === 'losses' && d.alerts.length ? '<span class="dot inline"></span>' : ''}</button>`).join('')}</nav>`;
  }

  // ---------- shared bits
  _tile(icon, bg, fg, label, value, sub, subColor) {
    return `<div class="tile"><div class="pa" style="background:${bg};color:${fg}">${ehIcon(icon, 18)}</div><div class="tt"><div class="t1">${ehEsc(label)}</div><div class="t2">${value}</div><div class="t3" style="color:${subColor || 'var(--secondary-text-color)'}">${sub}</div></div></div>`;
  }

  _box(title, hint, body) {
    return `<section class="box"><div class="hd"><h3>${ehEsc(title)}</h3>${hint ? `<span class="hint">${ehEsc(hint)}</span>` : ''}</div>${body}</section>`;
  }

  _alertTiles() {
    const d = this._data;
    if (!d.alerts.length) return '';
    const tiles = d.alerts.map((a) => {
      const tpl = this._t(`alerts.${a.kind}`);
      if (!Array.isArray(tpl)) return '';
      const p = {
        kwh: this._kwh(a.kwh),
        days: a.days ?? a.days_week ?? '',
        name: a.name ?? '',
        pct: a.relative != null ? `−${this._num((1 - a.relative) * 100, 0)} %` : '',
        unit: a.unit ?? '',
        from: a.periods?.length ? this._time(a.periods[0][0]) : a.start != null ? this._hm(a.start) : '',
        to: a.periods?.length ? this._time(a.periods[a.periods.length - 1][1]) : a.end != null ? this._hm(a.end) : '',
        battery: a.battery ?? '',
        cell: a.cell ?? '',
        kw: this._kw(a.kw),
        entities: (a.entities || []).join(', '),
      };
      if (a.kind === 'soiling') p.pct = this._pct(a.loss, 1);
      const color = a.severity === 'error' ? ['#FCEBEB', '#A32D2D'] : a.severity === 'info' ? ['#E6F1FB', '#185FA5'] : ['#FAEEDA', '#854F0B'];
      const icon = { clipping: 'alert-outline', string_lagging: 'solar-panel', shading: 'weather-cloudy-alert', soiling: 'water-off', cell_drift: 'scale-balance', battery_exchange: 'arrow-left-right', stale: 'power-plug-off-outline' }[a.kind];
      const fill = (s) => Object.entries(p).reduce((acc, [k, v]) => acc.replaceAll(`{${k}}`, v), s);
      return `<button class="alert" data-tab="losses"><div class="pa" style="background:${color[0]};color:${color[1]}">${ehIcon(icon, 18)}</div><div class="tt"><div class="a1">${ehEsc(fill(tpl[0]))}</div><div class="a2" style="color:${color[1]}">${ehEsc(fill(tpl[1]))}</div></div>${ehIcon('chevron-right', 18)}</button>`;
    });
    return `<div class="grid-auto">${tiles.join('')}</div>`;
  }

  // ---------- Overview
  _flow() {
    const d = this._data;
    const L = d.live;
    const fleet = d.batteries.fleet;
    const items = d.batteries.items;
    const pv = L.pv_kw || 0;
    const load = L.load_kw || 0;
    const grid = L.grid_kw || 0;
    const batt = L.battery_kw || 0;
    const w = (kw) => Math.max(2, Math.min(8, 2 + Math.abs(kw) * 1.4));
    const speed = (kw) => Math.max(1.2, 3 - Math.abs(kw) * 0.4).toFixed(2);
    const flowPath = (path, kw, color, reverse) => {
      if (Math.abs(kw) < 0.02) return `<path d="${path}" fill="none" stroke="var(--divider-color)" stroke-width="6" stroke-linecap="round"/>`;
      let dots = '';
      const n = Math.min(5, 2 + Math.round(Math.abs(kw)));
      const dur = speed(kw);
      for (let i = 0; i < n; i++) dots += `<circle r="${(w(kw) / 2).toFixed(1)}" fill="${color}"><animateMotion dur="${dur}s" begin="-${((i * dur) / n).toFixed(2)}s" repeatCount="indefinite" path="${path}" keyPoints="${reverse ? '1;0' : '0;1'}" keyTimes="0;1" calcMode="linear"/></circle>`;
      return `<path d="${path}" fill="none" stroke="var(--divider-color)" stroke-width="${w(kw) + 3}" stroke-linecap="round"/>${dots}`;
    };
    const pvHome = Math.min(pv, load);
    const node = (x, y, icon, bg, fg, label, value, sub, extra = '') =>
      `<foreignObject x="${x}" y="${y}" width="180" height="62"><div xmlns="http://www.w3.org/1999/xhtml" class="node"><div class="pa" style="background:${bg};color:${fg}">${ehIcon(icon, 18)}</div><div class="tt"><div class="t1">${label}</div><div class="t2">${value}</div>${sub ? `<div class="t3" style="color:${fg}">${sub}</div>` : ''}${extra}</div></div></foreignObject>`;
    const label = (x, y, kw) => (Math.abs(kw) < 0.02 ? '' : `<g><rect x="${x - 30}" y="${y - 11}" width="60" height="20" rx="10" fill="var(--card-background-color)" stroke="var(--divider-color)"/><text x="${x}" y="${y + 3}" text-anchor="middle" class="svgt">${this._kw(kw)}</text></g>`);
    const battName = items.length > 1 ? this._t('batteries_n', { n: items.length }) : this._t('battery');
    const battState = batt > 0.05 ? this._t('charging') : batt < -0.05 ? this._t('discharging') : fleet?.soc >= 99 ? this._t('full') : this._t('idle');
    const full = items.length === 1 && items[0].hours_to_full != null ? this._t('full_at', { v: this._time(Date.now() / 1000 + items[0].hours_to_full * 3600) }) : '';
    const socBar = fleet?.soc != null ? `<div class="soc"><div style="width:${fleet.soc}%"></div></div>` : '';
    let o = '<svg class="flow" viewBox="0 0 680 228" role="img" aria-label="Energy flow">';
    o += flowPath('M340 72 L340 156', pvHome, EH_GREEN);
    if (fleet) o += flowPath('M285 46 C185 46 120 84 120 156', batt, EH_TEAL, batt < 0);
    o += flowPath('M395 46 C495 46 560 84 560 156', grid, grid < 0 ? EH_BLUE : '#888780', grid > 0);
    o += label(378, 112, pvHome) + (fleet ? label(178, 74, batt) : '') + label(502, 74, grid);
    o += node(250, 12, 'white-balance-sunny', '#FAEEDA', '#854F0B', this._t('solar'), this._kw(pv), L.peak_share != null ? this._t('of_peak', { v: this._pct(L.peak_share) }) : '');
    if (fleet) o += node(30, 156, 'battery-charging', '#E1F5EE', '#0F6E56', `${battName} · ${battState}`, this._pct(fleet.soc / 100), full, socBar);
    o += node(250, 156, 'home-lightning-bolt-outline', '#EAF3DE', '#3B6D11', this._t('home'), this._kw(load), load > 0 ? this._t('solar_share', { v: this._pct(Math.min(pvHome / load, 1)) }) : '');
    o += node(470, 156, 'transmission-tower', '#E6F1FB', '#185FA5', `${this._t('grid')} · ${grid < -0.02 ? this._t('exporting') : grid > 0.02 ? this._t('importing') : this._t('idle')}`, this._kw(grid), '');
    return `${o}</svg>`;
  }

  _kpis() {
    const d = this._data;
    const T = d.today;
    const Y = d.yesterday;
    const trend = (a, b) => {
      if (a == null || b == null) return '';
      const pts = Math.round((a - b) * 100);
      return `<span style="color:${pts >= 0 ? 'var(--success-color,#43a047)' : 'var(--error-color,#db4437)'}">${pts >= 0 ? '▲' : '▼'} ${this._t('vs_yesterday', { v: `${Math.abs(pts)} ${this._t('pts')}` })}</span>`;
    };
    const losses = Object.entries(d.losses.today).filter(([k]) => !['potential', 'produced'].includes(k)).reduce((a, [, v]) => a + (v || 0), 0);
    const kp = (label, value, sub, color) => `<div class="kpi"><div class="k1">${ehEsc(label)}</div><div class="k2" ${color ? `style="color:${color}"` : ''}>${value}</div><div class="k3">${sub}</div></div>`;
    return `<div class="kpis">
      ${kp(this._t('self_consumption'), this._pct(T.self_consumption), trend(T.self_consumption, Y.self_consumption))}
      ${kp(this._t('self_sufficiency'), this._pct(T.self_sufficiency), trend(T.self_sufficiency, Y.self_sufficiency))}
      ${kp(this._t('saved'), this._eur(T.savings), ehEsc(this._t('resale', { v: this._eur(T.export_savings) })))}
      ${kp(this._t('losses'), this._kwh(losses), ehEsc(this._t('of_day', { v: this._eur(losses * (d.finances.import_price || 0)), p: d.losses.today.potential ? this._pct(losses / d.losses.today.potential) : '–' })), losses > 0.3 ? 'var(--error-color,#db4437)' : '')}
    </div>`;
  }

  _curve() {
    const d = this._data;
    const period = this._period;
    const seg = `<div class="seg">${['today', '7d', '30d', '12m'].map((p) => `<button class="${period === p ? 'on' : ''}" data-period="${p}">${ehEsc(this._t(`periods.${p}`))}</button>`).join('')}</div>`;
    const chip = (c, label, dash) => `<span class="chip"><span style="width:14px;border-top:2px ${dash ? 'dashed' : 'solid'} ${c}"></span>${ehEsc(label)}</span>`;
    const hatchChip = `<span class="chip"><svg width="14" height="10" aria-hidden="true"><rect width="14" height="10" fill="url(#ehhatch)" stroke="${EH_RED}" stroke-width=".6"/></svg>${ehEsc(this._t('clipping'))}</span>`;
    const hatchDef = `<defs><pattern id="ehhatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="${EH_RED}" fill-opacity=".08"/><line x1="0" y1="0" x2="0" y2="5" stroke="${EH_RED}" stroke-width="1.6" stroke-opacity=".7"/></pattern></defs>`;
    if (period !== 'today') {
      const rows = d.periods?.[period] || [];
      const W = 680;
      const x0 = 50;
      const x1 = 640;
      const max = Math.max(1, ...rows.map((r) => Math.max((r.pv || 0) + (r.clipped || 0), r.exp || 0, r.load || 0))) * 1.1;
      const Y = (v) => 190 - (v / max) * 160;
      const step = (x1 - x0) / Math.max(rows.length, 1);
      const bw = Math.max(Math.min(step * 0.62, 30), 3);
      let o = `<svg class="curve" viewBox="0 0 ${W} 214" role="img" aria-label="${ehEsc(this._t(`periods.${period}`))}">${hatchDef}`;
      for (const v of ehTicks(max)) {
        o += `<line x1="${x0}" x2="${x1}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--divider-color)" stroke-width=".5"/><text class="svgt" x="${x0 - 8}" y="${Y(v) + 4}" text-anchor="end">${this._num(v, v % 1 ? 1 : 0)}</text>`;
      }
      o += '<text class="svgt" x="16" y="18">kWh</text>';
      const loadPts = [];
      rows.forEach((r, i) => {
        const cx = x0 + step * (i + 0.5);
        const pvTop = Y(r.pv || 0);
        const label = period === '12m' ? new Date(`${r.d}-01T12:00`).toLocaleString(this._locale, { month: 'short' }) : new Date(`${r.d}T12:00`).toLocaleString(this._locale, period === '7d' ? { weekday: 'short' } : { day: 'numeric' });
        o += `<g><title>${ehEsc(label)} · ${ehEsc(this._t('production'))} ${this._kwh(r.pv)} · ${ehEsc(this._t('forecast'))} ${this._kwh(r.exp)} · ${ehEsc(this._t('consumption'))} ${this._kwh(r.load)}${r.clipped ? ` · ${ehEsc(this._t('clipped', { v: this._kwh(r.clipped) }))}` : ''}</title>`;
        o += `<rect x="${(cx - bw / 2).toFixed(1)}" y="${pvTop.toFixed(1)}" width="${bw.toFixed(1)}" height="${(190 - pvTop).toFixed(1)}" rx="2" fill="#FAC775" stroke="${EH_AMBER}" stroke-width=".6"/>`;
        if (r.clipped > 0.01) o += `<rect x="${(cx - bw / 2).toFixed(1)}" y="${Y((r.pv || 0) + r.clipped).toFixed(1)}" width="${bw.toFixed(1)}" height="${(pvTop - Y((r.pv || 0) + r.clipped)).toFixed(1)}" fill="url(#ehhatch)" stroke="${EH_RED}" stroke-width=".6"/>`;
        if (r.exp) o += `<line x1="${(cx - bw / 2 - 2).toFixed(1)}" x2="${(cx + bw / 2 + 2).toFixed(1)}" y1="${Y(r.exp).toFixed(1)}" y2="${Y(r.exp).toFixed(1)}" stroke="var(--secondary-text-color)" stroke-width="1.4" stroke-dasharray="3 2"/>`;
        o += '</g>';
        if (r.load != null) loadPts.push(`${cx.toFixed(1)} ${Y(r.load).toFixed(1)}`);
        const every = period === '30d' ? 5 : 1;
        if (i % every === 0 || i === rows.length - 1) o += `<text class="svgt" x="${cx.toFixed(1)}" y="208" text-anchor="middle">${ehEsc(label)}</text>`;
      });
      if (loadPts.length > 1) o += `<path d="M${loadPts.join(' L')}" fill="none" stroke="${EH_VIOLET}" stroke-width="1.8"/>${loadPts.map((p) => `<circle cx="${p.split(' ')[0]}" cy="${p.split(' ')[1]}" r="2.2" fill="${EH_VIOLET}"/>`).join('')}`;
      o += '</svg>';
      const total = rows.reduce((a, r) => a + (r.pv || 0), 0);
      const totalExp = rows.reduce((a, r) => a + (r.exp || 0), 0);
      const legend = `${chip(EH_AMBER, this._t('production'))}${chip('var(--secondary-text-color)', this._t('forecast'), true)}${chip(EH_VIOLET, this._t('consumption'))}${rows.some((r) => r.clipped > 0.01) ? hatchChip : ''}`;
      this._curveMeta = null;
      return this._box(this._t('production'), '', `<div class="hd sub">${seg}<span class="hint">${ehEsc(this._t('produced_of', { a: this._kwh(total), b: this._kwh(totalExp) }))}</span></div><div class="legend">${legend}</div>${o}`);
    }
    const rows = d.curve;
    if (!rows.length) return '';
    const W = 680;
    const H = 214;
    const x0 = 50;
    const x1 = 630;
    const start = new Date(d.generated);
    start.setHours(5, 0, 0, 0);
    const t0 = start.getTime() / 1000;
    const t1 = t0 + 17 * 3600;
    const max = Math.max(1, ...rows.map((r) => Math.max(r.pv || 0, r.exp || 0, r.load || 0)), d.inverter_max_kw || 0) * 1.1;
    const X = (t) => x0 + ((t - t0) / (t1 - t0)) * (x1 - x0);
    const Y = (v) => 190 - (Math.min(v, max) / max) * 160;
    const YS = (s) => 190 - (s / 100) * 160;
    const inRange = rows.filter((r) => r.t >= t0 && r.t <= t1);
    const line = (key, f = Y) => inRange.filter((r) => r[key] != null).map((r, i) => `${i ? 'L' : 'M'}${X(r.t).toFixed(1)} ${f(r[key]).toFixed(1)}`).join(' ');
    let o = `<svg class="curve" viewBox="0 0 ${W} ${H}" role="img" aria-label="${ehEsc(this._t('periods.today'))}">${hatchDef}`;
    for (const v of ehTicks(max)) {
      o += `<line x1="${x0}" x2="${x1}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--divider-color)" stroke-width=".5"/><text class="svgt" x="${x0 - 8}" y="${Y(v) + 4}" text-anchor="end">${this._num(v, v % 1 ? 1 : 0)}</text>`;
    }
    o += `<text class="svgt" x="16" y="18">kW</text><text class="svgt" x="${x1 + 6}" y="34">100</text><text class="svgt" x="${x1 + 6}" y="194">0 %</text>`;
    const pv = line('pv');
    if (pv && inRange.length) o += `<path d="${pv} L${X(inRange[inRange.length - 1].t).toFixed(1)} 190 L${X(inRange[0].t).toFixed(1)} 190 Z" fill="#FAC775" fill-opacity=".5"/>`;
    // Clipping: the energy between the forecast and the plateau, hatched
    const clipped = d.losses.clipping_periods || [];
    for (const [a, b] of clipped) {
      const seg2 = inRange.filter((r) => r.t >= a && r.t <= b && r.exp != null && r.pv != null);
      if (seg2.length < 2) continue;
      const top = seg2.map((r) => `${X(r.t).toFixed(1)} ${Y(Math.max(r.exp, r.pv)).toFixed(1)}`);
      const bottom = seg2.map((r) => `${X(r.t).toFixed(1)} ${Y(r.pv).toFixed(1)}`).reverse();
      o += `<path d="M${top.join(' L')} L${bottom.join(' L')} Z" fill="url(#ehhatch)" stroke="${EH_RED}" stroke-width=".8"/>`;
    }
    if (pv) o += `<path d="${pv}" fill="none" stroke="${EH_AMBER}" stroke-width="2"/>`;
    const exp = line('exp');
    if (exp) o += `<path d="${exp}" fill="none" stroke="var(--secondary-text-color)" stroke-width="1.3" stroke-dasharray="4 4"/>`;
    const load = line('load');
    if (load) o += `<path d="${load}" fill="none" stroke="${EH_VIOLET}" stroke-width="1.8"/>`;
    const soc = line('soc', YS);
    if (soc) o += `<path d="${soc}" fill="none" stroke="${EH_TEAL}" stroke-width="1.5"/>`;
    if (d.inverter_max_kw) o += `<line x1="${x0}" x2="${x1}" y1="${Y(d.inverter_max_kw)}" y2="${Y(d.inverter_max_kw)}" stroke="${EH_RED}" stroke-dasharray="2 3"/><text class="svgt" x="${x1 - 4}" y="${Y(d.inverter_max_kw) - 6}" text-anchor="end" style="fill:${EH_RED}">${ehEsc(this._t('inverter_max', { v: this._kw(d.inverter_max_kw) }))}</text>`;
    const last = inRange[inRange.length - 1];
    if (last) o += `<line x1="${X(last.t)}" x2="${X(last.t)}" y1="30" y2="190" stroke="var(--secondary-text-color)" stroke-width=".5" stroke-dasharray="3 3"/><circle cx="${X(last.t)}" cy="${Y(last.pv || 0)}" r="4.5" fill="${EH_AMBER}" stroke="var(--card-background-color)" stroke-width="2"/>`;
    for (let h = 6; h <= 21; h += 3) {
      const t = t0 + (h - 5) * 3600;
      o += `<text class="svgt" x="${X(t)}" y="208" text-anchor="middle">${this._lang === 'fr' ? `${h} h` : `${h}:00`}</text>`;
    }
    o += `<line class="hov" x1="0" x2="0" y1="30" y2="190" stroke="var(--secondary-text-color)" stroke-width=".5" style="display:none"/><rect class="hit" x="${x0}" y="30" width="${x1 - x0}" height="160" fill="transparent"/></svg>`;
    const legend = `${chip(EH_AMBER, this._t('production'))}${chip('var(--secondary-text-color)', this._t('forecast'), true)}${chip(EH_VIOLET, this._t('consumption'))}${chip(EH_TEAL, this._t('battery_pct'))}${chip(EH_RED, 'Pmax', true)}${clipped.length ? hatchChip : ''}`;
    this._curveMeta = { t0, t1, x0, x1, max, rows: inRange };
    return this._box(this._t('production'), '', `<div class="hd sub">${seg}<span class="hint">${ehEsc(this._t('produced_of', { a: this._kwh(d.today.pv_kwh), b: this._kwh(d.today.expected_kwh) }))}</span></div><div class="legend">${legend}</div><div class="curvewrap">${o}<div class="tip"></div></div><div class="hint">${ehEsc(this._t('hover_hint'))}</div>`);
  }

  _overview() {
    return `${this._flow()}${this._kpis()}${this._curve()}${this._alertTiles()}`;
  }

  // ---------- Production
  _production() {
    const d = this._data;
    const P = d.production;
    const T = d.today;
    const prRange = `${this._num(0.8, 2)} – ${this._num(0.95, 2)}`;
    let o = `<div class="grid4">
      ${this._tile('gauge', '#FAEEDA', '#854F0B', this._t('yield'), T.specific_yield != null ? `${this._num(T.specific_yield, 2)} kWh/kWp` : '–', d.kwp_estimated ? this._t('estimated') : this._t('kwp', { v: this._num(d.kwp, 1) }))}
      ${this._tile('target', '#EAF3DE', '#3B6D11', this._t('pr'), this._pct(T.epi), this._t('pr_range', { v: prRange }), EH_GREEN)}
      ${this._tile('chart-line', '#FCEBEB', '#A32D2D', this._t('peak_day'), this._kw(T.peak_kw), d.inverter_max_kw && T.peak_kw >= 0.97 * d.inverter_max_kw ? this._t('reached_limit') : T.peak_at ? this._time(new Date(T.peak_at).getTime() / 1000) : '', d.inverter_max_kw && T.peak_kw >= 0.97 * d.inverter_max_kw ? EH_RED : '')}
      ${this._tile('calendar-month', '#FAEEDA', '#854F0B', this._t('this_month'), this._kwh(P.month_kwh), P.month_expected ? this._t('of_expected', { v: this._pct(P.month_kwh / P.month_expected) }) : '')}
    </div>`;
    if (P.units.length) {
      const per = Math.ceil(P.units.length / 2);
      let svg = '<svg viewBox="0 0 640 200" class="roof" role="img" aria-label="Roof">';
      svg += '<polygon points="60,180 580,180 520,20 120,20" fill="#B4553A" fill-opacity=".18" stroke="#B4553A" stroke-opacity=".4"/>';
      const rowsN = P.units.length > per ? 2 : 1;
      P.units.forEach((u, i) => {
        const row = Math.floor(i / per);
        const c = i % per;
        const y0 = 30 + row * (152 / rowsN);
        const y1 = y0 + 152 / rowsN - 10;
        const tf = (y) => (y - 20) / 160;
        const L0 = 120 - 60 * tf(y0);
        const R0 = 520 + 60 * tf(y0);
        const L1 = 120 - 60 * tf(y1);
        const R1 = 520 + 60 * tf(y1);
        const w0 = (R0 - L0) / per;
        const w1 = (R1 - L1) / per;
        const g = 3;
        const pct = u.pct ?? 0;
        const col = pct < 70 ? EH_RED : pct < 92 ? '#EF9F27' : EH_AMBER;
        const pts = [[L0 + c * w0 + g, y0], [L0 + (c + 1) * w0 - g, y0], [L1 + (c + 1) * w1 - g, y1], [L1 + c * w1 + g, y1]];
        const cx = pts.reduce((a, p) => a + p[0], 0) / 4;
        const cy = (y0 + y1) / 2;
        svg += `<polygon points="${pts.map((p) => p.join(',')).join(' ')}" fill="${col}" fill-opacity="${(0.3 + (0.7 * pct) / 100).toFixed(2)}" stroke="#2F4A70" stroke-opacity=".5"><title>${ehEsc(u.name)} · ${pct} % · ${this._kwh(u.kwh)}</title></polygon><text class="svgt dark" x="${cx}" y="${cy - 3}" text-anchor="middle">${ehEsc(u.name)}</text><text class="svgth dark" x="${cx}" y="${cy + 13}" text-anchor="middle">${u.pct ?? '–'}</text>`;
      });
      svg += '</svg>';
      const legend = `<span class="chip"><span class="sw" style="background:${EH_AMBER}"></span>≥ 92 %</span><span class="chip"><span class="sw" style="background:#EF9F27"></span>70 – 92 %</span><span class="chip"><span class="sw" style="background:${EH_RED}"></span>&lt; 70 %</span>`;
      o += this._box(this._t('roof'), this._t('roof_hint'), `${svg}<div class="legend">${legend}</div>`);
    }
    if (P.strings.length) {
      const best = Math.max(...P.strings.map((s) => s.kwh || 0), 0.001);
      const rows = P.strings
        .map((s) => {
          const lag = s.lagging_days >= 3;
          return `<div class="barrow"><span>${ehEsc(s.name)}</span><div class="meter"><div style="width:${((s.kwh || 0) / best) * 100}%;background:${lag ? '#EF9F27' : EH_AMBER}"></div></div><span style="color:${lag ? EH_AMBER : 'var(--secondary-text-color)'}">${this._kwh(s.kwh)}${s.relative != null ? ` · ${s.relative >= 1 ? '+' : '−'}${this._num(Math.abs(s.relative - 1) * 100, 0)} %` : ''}</span></div>`;
        })
        .join('');
      o += this._box(this._t('strings'), '', rows);
    }
    const epi = P.epi_30d;
    let prSvg = '<svg class="mini" viewBox="0 0 300 120" role="img" aria-label="PR">';
    if (epi.length > 1) {
      const vals = epi.map((e) => e.epi);
      const lo = Math.min(...vals, 0.6);
      const hi = Math.max(...vals, 1);
      const X = (i) => 10 + (i / (epi.length - 1)) * 280;
      const Y = (v) => 100 - ((v - lo) / (hi - lo)) * 84;
      prSvg += `<path d="${epi.map((e, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)} ${Y(e.epi).toFixed(1)}`).join(' ')}" fill="none" stroke="${EH_AMBER}" stroke-width="2" stroke-linejoin="round"/>`;
      epi.forEach((e, i) => {
        if (e.rain) prSvg += `<line x1="${X(i)}" x2="${X(i)}" y1="16" y2="100" stroke="${EH_BLUE}" stroke-width=".6" stroke-dasharray="2 2"/><path d="M${X(i)} 6 C${X(i) - 4} 12 ${X(i) - 4} 16 ${X(i)} 16 C${X(i) + 4} 16 ${X(i) + 4} 12 ${X(i)} 6 Z" fill="${EH_BLUE}"/>`;
      });
    }
    prSvg += '<line x1="10" x2="290" y1="100" y2="100" stroke="var(--divider-color)"/></svg>';
    const soil = d.trends.soiling;
    const soilText = soil.learning ? this._t('learning', { d: soil.days, n: soil.needed }) : `${this._t('soiling_trend')} −${this._pct(soil.loss, 1)}`;
    const deg = d.trends.degradation;
    const degText = deg.learning ? this._t('learning', { d: deg.days, n: deg.needed }) : this._t('per_year', { v: `${this._num(deg.rate, 2)} %` });
    const months = P.months;
    let mSvg = '<svg class="mini" viewBox="0 0 300 120" role="img" aria-label="Months">';
    const mmax = Math.max(1, ...months.map((m) => Math.max(m.kwh, m.expected || 0)));
    months.forEach((m, i) => {
      const x = 10 + i * 24;
      const h = (m.kwh / mmax) * 90;
      const he = ((m.expected || 0) / mmax) * 90;
      mSvg += `<rect x="${x}" y="${100 - h}" width="16" height="${h}" rx="3" fill="#FAC775" stroke="${EH_AMBER}" stroke-width=".5"><title>${m.m} · ${this._kwh(m.kwh)}</title></rect>`;
      if (he) mSvg += `<line x1="${x - 2}" x2="${x + 18}" y1="${100 - he}" y2="${100 - he}" stroke="var(--secondary-text-color)" stroke-width="1.5"/>`;
      mSvg += `<text class="svgt" x="${x + 8}" y="114" text-anchor="middle">${new Date(`${m.m}-01`).toLocaleString(this._hass?.locale?.language || 'en', { month: 'narrow' })}</text>`;
    });
    mSvg += '</svg>';
    o += `<div class="grid2">${this._box(this._t('pr_30'), this._t('rain'), `${prSvg}<div class="hint">${ehEsc(soilText)} · ${ehEsc(this._t('degradation'))} ${ehEsc(degText)}</div>`)}${this._box(this._t('months_12'), this._t('expected_line'), mSvg)}</div>`;
    return o;
  }

  // ---------- Batteries
  _batteries() {
    const d = this._data;
    const B = d.batteries;
    if (!B.items.length) return `<div class="empty">${ehEsc(this._t('none'))}</div>`;
    const fleet = B.fleet;
    let o = `<div class="grid4">
      ${this._tile('battery-70', '#E1F5EE', '#0F6E56', this._t('fleet'), this._pct(fleet.soc / 100), `${this._num(fleet.stored_kwh, 1)} / ${this._num(fleet.capacity_kwh, 1)} kWh`, '#0F6E56')}
      ${this._tile('sync', '#E1F5EE', '#0F6E56', this._t('net_power'), `${fleet.power_kw >= 0 ? '+' : '−'}${this._kw(fleet.power_kw)}`, this._t('n_charging', { c: fleet.charging, d: fleet.discharging }))}
      ${this._tile('timer-sand', '#E6F1FB', '#185FA5', this._t('autonomy'), B.autonomy_h != null ? `${this._num(B.autonomy_h, 1)} h` : '–', this._t('autonomy_sub', { v: this._kw(d.live.load_kw) }))}
      ${this._tile('arrow-left-right', '#FAEEDA', '#854F0B', this._t('exchange'), fleet.exchange_kw > 0.05 ? this._kw(fleet.exchange_kw) : this._t('none'), fleet.exchange_kw > 0.05 ? this._t('to_avoid') : '', EH_AMBER)}
    </div>`;
    if (B.items.length > 1) {
      const cards = [`<button class="bcard ${this._battery === 'all' ? 'on' : ''}" data-battery="all"><div class="pa" style="background:#E1F5EE;color:#0F6E56">${ehIcon('layers-triple-outline', 18)}</div><div class="tt"><div class="a1">${ehEsc(this._t('all'))}</div><div class="t3">${ehEsc(this._t('compare'))}</div></div></button>`];
      for (const b of B.items) cards.push(`<button class="bcard ${this._battery === b.key ? 'on' : ''}" data-battery="${ehEsc(b.key)}">${this._miniBattery(b.soc, b.state)}<div class="tt"><div class="a1">${ehEsc(b.name)} <span class="muted">${this._pct(b.soc / 100)}</span></div><div class="t3" style="color:${b.state === 'discharging' ? EH_BLUE : EH_TEAL}">${ehEsc(this._t(b.state))}${b.power_kw ? ` · ${this._kw(b.power_kw)}` : ''}</div><span class="brand">${ehEsc(b.platform)}</span></div></button>`);
      o += `<div class="grid-auto">${cards.join('')}</div>`;
    }
    const selected = B.items.length === 1 ? B.items[0] : B.items.find((b) => b.key === this._battery);
    if (!selected) {
      const metric = (get, max, fmt) => B.items.map((b) => `<div class="barrow"><span>${ehEsc(b.name)}</span><div class="meter"><div style="width:${Math.max(2, ((get(b) || 0) / max) * 100)}%;background:${EH_TEAL}"></div></div><span>${fmt(get(b))}</span></div>`).join('');
      o += `<div class="grid2">${this._box(this._t('soc'), '', metric((b) => b.soc, 100, (v) => this._pct(v / 100)))}${this._box(this._t('health'), '', metric((b) => b.soh, 100, (v) => (v == null ? '–' : `${this._num(v, 0)} %`)))}</div>`;
      o += `<div class="grid2">${this._box(this._t('rte'), '', metric((b) => b.rte, 1, (v) => this._pct(v)))}${this._box(this._t('cycles'), '', metric((b) => b.cycles, Math.max(...B.items.map((b) => b.cycles || 0), 1), (v) => (v == null ? '–' : this._num(v, 0))))}</div>`;
      const cap = B.items.map((b, i) => `<div style="flex:${b.capacity_kwh};background:${['#0F6E56', EH_TEAL, '#5DCAA5', '#9FE1CB'][i % 4]}">${ehEsc(b.name)} ${this._num(b.capacity_kwh, 1)} kWh</div>`).join('');
      o += this._box(this._t('capacity_share'), `${this._num(fleet.capacity_kwh, 1)} kWh`, `<div class="stack">${cap}</div>`);
      return o;
    }
    return o + this._batteryDetail(selected);
  }

  _miniBattery(soc, state) {
    const h = Math.round((30 * (soc || 0)) / 100);
    return `<svg width="22" height="40" viewBox="0 0 22 40" aria-hidden="true"><rect x="7" y="1" width="8" height="4" rx="1.5" fill="var(--secondary-text-color)"/><rect x="2" y="5" width="18" height="34" rx="4" fill="none" stroke="var(--secondary-text-color)" stroke-width="1.5"/><rect x="5" y="${36 - h}" width="12" height="${h}" rx="2" fill="${state === 'discharging' ? EH_BLUE : '#5DCAA5'}"/></svg>`;
  }

  // The selected battery drawn as a wall unit: its level, its state and power, its reserve
  _bigBattery(b) {
    const soc = b.soc || 0;
    const h = Math.round((150 * soc) / 100);
    const res = Math.round((150 * (b.reserve || 0)) / 100);
    const col = b.state === 'discharging' ? EH_BLUE : EH_TEAL;
    const anim = b.state === 'charging' ? `<animate attributeName="opacity" values="1;.35;1" dur="1.6s" repeatCount="indefinite"/>` : '';
    let o = `<svg class="bigbatt" viewBox="0 0 134 200" role="img" aria-label="${ehEsc(b.name)} ${this._pct(soc / 100)}">`;
    o += `<rect x="44" y="6" width="32" height="10" rx="3" fill="var(--secondary-text-color)"/><rect x="14" y="16" width="92" height="176" rx="14" fill="var(--secondary-background-color)" stroke="var(--secondary-text-color)" stroke-width="2"/>`;
    o += `<clipPath id="ehbb"><rect x="22" y="30" width="76" height="150" rx="8"/></clipPath><g clip-path="url(#ehbb)"><rect x="22" y="${180 - h}" width="76" height="${h}" fill="${col}" fill-opacity=".85">${anim}</rect><rect x="22" y="${180 - h}" width="76" height="4" fill="#fff" fill-opacity=".35"/></g>`;
    o += `<line x1="18" x2="102" y1="${180 - res}" y2="${180 - res}" stroke="${EH_RED}" stroke-dasharray="3 3"/><text class="svgt" x="104" y="${183 - res}" style="font-size:9px">${this._num(b.reserve, 0)} %</text>`;
    o += `<text x="60" y="${soc > 55 ? 100 : 70}" text-anchor="middle" class="svgth" style="font-size:22px;fill:${soc > 55 ? '#fff' : 'var(--primary-text-color)'}">${this._num(soc, 0)} %</text>`;
    if (b.state === 'charging') o += `<path d="M64 112 L52 132 H60 L56 150 L70 126 H62 Z" fill="#fff"/>`;
    if (b.state === 'discharging') o += `<path d="M60 118 V146 M50 136 L60 146 L70 136" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
    return `${o}</svg>`;
  }

  _batteryDetail(b) {
    const d = this._data;
    const stateColor = b.state === 'discharging' ? EH_BLUE : EH_TEAL;
    const head = `<div class="battrow"><div class="bbwrap">${this._bigBattery(b)}<div class="a1">${ehEsc(b.name)}</div><div class="t3" style="color:${stateColor}">${ehEsc(this._t(b.state))}${b.power_kw ? ` · ${this._kw(b.power_kw)}` : ''}</div><span class="brand">${ehEsc(b.platform)} · ${ehEsc(this._t(`coupling.${b.coupling}`))}</span></div><div class="grid3">
      ${this._tile('heart-pulse', '#E1F5EE', '#0F6E56', this._t('health'), b.soh != null ? `${this._num(b.soh, 0)} %` : '–', b.soh_estimated ? this._t('estimated') : this._t('measured', { a: this._num((b.capacity_kwh * (b.soh || 0)) / 100, 1), b: `${this._num(b.capacity_kwh, 1)} kWh` }))}
      ${this._tile('sync', '#E1F5EE', '#0F6E56', this._t('cycles'), b.cycles != null ? this._num(b.cycles, 0) : '–', b.cycles_estimated ? this._t('estimated') : '')}
      ${this._tile('arrow-left-right', '#E1F5EE', '#0F6E56', this._t('rte'), this._pct(b.rte), this._t('days_30'))}
      ${this._tile('timer-sand', '#E6F1FB', '#185FA5', this._t('autonomy'), b.autonomy_h != null ? `${this._num(b.autonomy_h, 1)} h` : '–', this._t('autonomy_sub', { v: this._kw(d.live.load_kw) }))}
      ${this._tile('thermometer', '#EAF3DE', '#3B6D11', this._t('temperature'), b.temperature != null ? `${this._num(b.temperature, 0)} °C` : '–', '')}
      ${this._tile('battery-70', '#E1F5EE', '#0F6E56', this._t('capacity'), `${this._num(b.capacity_kwh, 1)} kWh`, b.capacity_estimated ? this._t('estimated') : this._t('reserve', { v: `${this._num(b.reserve, 0)} %` }))}
    </div></div>`;
    let o = this._box(b.name, b.platform, head);
    o += `<div class="grid2">${this._box(this._t('soc_today'), b.soc_projection?.length ? this._t('projection_dashed') : '', this._socChart(b))}${this._box(this._t('soh_3y'), b.soh_trend ? this._t('per_year', { v: `${this._num(b.soh_trend.per_year, 2)} %` }) : '', this._sohChart(b))}</div>`;
    if (b.modules?.length) {
      const mods = b.modules.map((m) => `<div class="tile">${this._miniBattery(m.soc, b.state)}<div class="tt"><div class="a1">${ehEsc(m.name)}</div><div class="t3">${m.soc != null ? this._pct(m.soc / 100) : '–'}${m.voltage != null ? ` · ${this._num(m.voltage, 1)} V` : ''}${m.temperature != null ? ` · ${this._num(m.temperature, 1)} °C` : ''}</div></div></div>`).join('');
      o += this._box(this._t('modules'), `${b.modules.length}`, `<div class="grid-auto">${mods}</div>`);
    }
    return o + this._cells(b);
  }

  _socChart(b) {
    const pts = b.soc_today || [];
    if (pts.length < 2) return `<div class="hint">${ehEsc(this._t('learning_short'))}</div>`;
    const start = new Date(this._data.generated);
    start.setHours(0, 0, 0, 0);
    const t0 = start.getTime() / 1000;
    const X = (t) => 30 + ((t - t0) / 86400) * 600;
    const Y = (v) => 110 - (v / 100) * 96;
    let o = `<svg class="mini m" viewBox="0 0 640 128" role="img" aria-label="${ehEsc(this._t('soc_today'))}">`;
    for (const v of [0, 50, 100]) o += `<line x1="30" x2="630" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--divider-color)" stroke-width=".5"/><text class="svgt" x="24" y="${Y(v) + 3}" text-anchor="end">${v}</text>`;
    o += `<line x1="30" x2="630" y1="${Y(b.reserve)}" y2="${Y(b.reserve)}" stroke="${EH_RED}" stroke-width=".8" stroke-dasharray="3 3"/>`;
    const path = pts.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(' ');
    o += `<path d="${path} L${X(pts[pts.length - 1][0]).toFixed(1)} 110 L${X(pts[0][0]).toFixed(1)} 110 Z" fill="${EH_TEAL}" fill-opacity=".12"/><path d="${path}" fill="none" stroke="${EH_TEAL}" stroke-width="2"/>`;
    const proj = b.soc_projection || [];
    if (proj.length > 1) o += `<path d="${proj.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(' ')}" fill="none" stroke="${EH_TEAL}" stroke-width="1.6" stroke-dasharray="4 4"/>`;
    const last = pts[pts.length - 1];
    o += `<circle cx="${X(last[0])}" cy="${Y(last[1])}" r="4" fill="${EH_TEAL}" stroke="var(--card-background-color)" stroke-width="2"/>`;
    for (let h = 0; h <= 24; h += 6) o += `<text class="svgt" x="${X(t0 + h * 3600)}" y="124" text-anchor="${h === 24 ? 'end' : h === 0 ? 'start' : 'middle'}">${this._lang === 'fr' ? `${h} h` : `${h}:00`}</text>`;
    return `${o}</svg>`;
  }

  _sohChart(b) {
    const tr = b.soh_trend;
    if (!tr) return `<div class="hint">${ehEsc(this._t('learning_short'))}</div>`;
    const day = (s) => new Date(`${s}T12:00`).getTime() / 86400000;
    const all = [...tr.points, tr.projected];
    const d0 = day(all[0][0]);
    const d1 = day(tr.projected[0]);
    const lo = Math.floor(Math.min(...all.map((p) => p[1])) - 2);
    const X = (s) => 30 + ((day(s) - d0) / Math.max(d1 - d0, 1)) * 600;
    const Y = (v) => 110 - ((v - lo) / (100 - lo)) * 96;
    let o = `<svg class="mini m" viewBox="0 0 640 128" role="img" aria-label="${ehEsc(this._t('soh_3y'))}">`;
    for (const v of [lo, Math.round((lo + 100) / 2), 100]) o += `<line x1="30" x2="630" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--divider-color)" stroke-width=".5"/><text class="svgt" x="24" y="${Y(v) + 3}" text-anchor="end">${v}</text>`;
    o += `<path d="${tr.points.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(' ')}" fill="none" stroke="${EH_TEAL}" stroke-width="2"/>`;
    const lastP = tr.points[tr.points.length - 1];
    o += `<path d="M${X(lastP[0]).toFixed(1)} ${Y(lastP[1]).toFixed(1)} L${X(tr.projected[0]).toFixed(1)} ${Y(tr.projected[1]).toFixed(1)}" stroke="${EH_TEAL}" stroke-width="1.6" stroke-dasharray="4 4"/>`;
    o += `<circle cx="${X(lastP[0])}" cy="${Y(lastP[1])}" r="4" fill="${EH_TEAL}" stroke="var(--card-background-color)" stroke-width="2"/><circle cx="${X(tr.projected[0])}" cy="${Y(tr.projected[1])}" r="4" fill="var(--card-background-color)" stroke="${EH_TEAL}" stroke-width="2"/><text class="svgt" x="${X(tr.projected[0]) - 6}" y="${Y(tr.projected[1]) - 8}" text-anchor="end">${this._num(tr.projected[1], 1)} %</text>`;
    const y0 = new Date(`${all[0][0]}T12:00`).getFullYear();
    const y1 = new Date(`${tr.projected[0]}T12:00`).getFullYear();
    for (let y = y0 + 1; y <= y1; y++) o += `<text class="svgt" x="${X(`${y}-01-01`)}" y="124" text-anchor="middle">${y}</text>`;
    o += `<line x1="${X(lastP[0])}" x2="${X(lastP[0])}" y1="14" y2="110" stroke="var(--secondary-text-color)" stroke-width=".5" stroke-dasharray="3 3"/>`;
    return `${o}</svg>`;
  }

  _cells(b) {
    const c = b.cells;
    if (!c) return this._box(this._t('cells'), '', `<div class="hint">${ehEsc(this._t('no_cells'))}</div>`);
    const s = c.summary;
    const n = c.voltages.length;
    const mean = c.voltages.reduce((a, v) => a + v, 0) / n;
    const metric = this._cellMetric === 'temperature' && !c.temps?.length ? 'deviation' : this._cellMetric;
    const per = c.per_module || Math.min(n, 16);
    const rows = Math.ceil(n / per);
    const tMin = c.temps?.length ? Math.min(...c.temps) : 0;
    const tMax = c.temps?.length ? Math.max(...c.temps) : 1;
    const cell = (i) => {
      const v = c.voltages[i];
      const dev = (v - mean) * 1000;
      let bg;
      let label;
      if (metric === 'voltage') {
        bg = `rgba(29,158,117,${(0.2 + Math.min(1, (v - s.min_v) / Math.max(s.max_v - s.min_v, 0.001)) * 0.65).toFixed(2)})`;
        label = this._num(v, 3);
      } else if (metric === 'temperature') {
        const k = (c.temps[i] - tMin) / Math.max(tMax - tMin, 0.1);
        bg = `rgba(${Math.round(55 + 180 * k)},${Math.round(138 - 60 * k)},${Math.round(221 - 160 * k)},.75)`;
        label = this._num(c.temps[i], 1);
      } else {
        bg = Math.abs(dev) < 4 ? 'rgba(136,135,128,.18)' : dev < 0 ? `rgba(239,159,39,${Math.min(1, 0.25 + -dev / 36).toFixed(2)})` : `rgba(55,138,221,${Math.min(1, 0.25 + dev / 14).toFixed(2)})`;
        label = `${dev >= 0 ? '+' : ''}${Math.round(dev)}`;
      }
      const bal = c.balancing?.includes(i) ? '<span class="baldot"></span>' : '';
      const drift = c.drifting?.includes(i) ? ' drift' : '';
      return `<button class="cell${this._cell === i ? ' sel' : ''}${drift}" data-cell="${i}" style="background:${bg}" title="C${(i % per) + 1} · ${this._num(v, 3)} V">${label}${bal}</button>`;
    };
    let grid = '';
    for (let r = 0; r < rows; r++) {
      const cellsRow = [];
      for (let i = r * per; i < Math.min(n, (r + 1) * per); i++) cellsRow.push(cell(i));
      grid += `<div class="cellrow"><span class="rowlab">${c.per_module ? ehEsc(b.modules?.[r]?.name || `M${r + 1}`) : ''}</span><div class="cells" style="grid-template-columns:repeat(${per},1fr)">${cellsRow.join('')}</div></div>`;
    }
    const metrics = ['deviation', 'voltage', ...(c.temps?.length ? ['temperature'] : [])];
    const seg = `<div class="seg">${metrics.map((m) => `<button class="${metric === m ? 'on' : ''}" data-cellmetric="${m}">${ehEsc(this._t(m))}</button>`).join('')}</div>`;
    const legendBits = metric === 'deviation' ? `<span class="chip"><span class="sw" style="background:rgba(239,159,39,.8)"></span>${ehEsc(this._t('low'))}</span><span class="chip"><span class="sw" style="background:rgba(136,135,128,.25)"></span>± 4 mV</span><span class="chip"><span class="sw" style="background:rgba(55,138,221,.8)"></span>${ehEsc(this._t('high'))}</span>` : '';
    const legend = `<div class="legend">${legendBits}${c.balancing?.length ? `<span class="chip"><span class="baldot static"></span>${ehEsc(this._t('balancing'))}</span>` : ''}${c.drifting?.length ? `<span class="chip"><span class="sw" style="outline:2px solid ${EH_RED};background:none"></span>${ehEsc(this._t('drifting'))}</span>` : ''}</div>`;
    const tiles = `<div class="grid4">
      ${this._tile('flash-outline', '#E1F5EE', '#0F6E56', this._t('max'), `${this._num(s.max_v, 3)} V`, this._cellName(c, s.max_index, b))}
      ${this._tile('flash-outline', '#FAEEDA', '#854F0B', this._t('min'), `${this._num(s.min_v, 3)} V`, this._cellName(c, s.min_index, b), EH_AMBER)}
      ${this._tile('scale-balance', '#FAEEDA', '#854F0B', this._t('spread'), `${this._num(s.spread_mv, 0)} mV`, this._t('of_threshold', { t: `${c.threshold_mv} mV` }), EH_AMBER)}
      ${this._tile('sync', '#EEEDFE', '#3C3489', this._t('balancing'), c.balancing?.length ? this._t('n_cells', { n: c.balancing.length }) : this._t('none'), '')}
    </div>`;
    let o = this._box(`${this._t('cells')} · ${n}`, c.per_module ? this._t('modules_x_cells', { m: rows, c: per }) : '', `${tiles}<div class="hd" style="margin-top:10px">${seg}</div>${grid}${legend}`);
    if (this._cell != null && this._cell < n) o += this._cellDetail(b, this._cell, mean);
    o += this._box(this._t('spread_trend'), c.days_to_threshold != null ? this._t('threshold_in', { t: `${c.threshold_mv} mV`, d: this._num(c.days_to_threshold, 0) }) : this._t('stable'), this._spreadChart(c));
    return o;
  }

  _cellName(c, i, b) {
    if (!c.per_module) return `C${i + 1}`;
    const m = Math.floor(i / c.per_module);
    return `${b.modules?.[m]?.name || `M${m + 1}`} · C${(i % c.per_module) + 1}`;
  }

  _cellDetail(b, i, mean) {
    const c = b.cells;
    const v = c.voltages[i];
    const dev = (v - mean) * 1000;
    const hist = c.history?.[i] || [];
    const slope = c.drift_mv_day?.[i];
    let spark = '';
    if (hist.length > 1) {
      const lo = Math.min(...hist, -5);
      const hi = Math.max(...hist, 5);
      const X = (k) => 10 + (k / (hist.length - 1)) * 580;
      const Y = (val) => 84 - ((val - lo) / (hi - lo)) * 72;
      spark = `<svg class="mini m" viewBox="0 0 600 104" role="img" aria-label="30 d"><line x1="10" x2="590" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--divider-color)"/><path d="${hist.map((val, k) => `${k ? 'L' : 'M'}${X(k).toFixed(1)} ${Y(val).toFixed(1)}`).join(' ')}" fill="none" stroke="${c.drifting?.includes(i) ? EH_RED : EH_TEAL}" stroke-width="2"/><text class="svgt" x="10" y="100">${ehEsc(this._t('days_30'))}</text><text class="svgt" x="590" y="100" text-anchor="end">mV</text></svg>`;
    }
    const diag = c.drifting?.includes(i) ? this._t('diag_drift', { v: `${slope > 0 ? '+' : ''}${this._num(slope, 1)}` }) : this._t('diag_stable');
    const tiles = `<div class="grid4">
      ${this._tile('flash-outline', '#E1F5EE', '#0F6E56', this._t('voltage'), `${this._num(v, 3)} V`, '')}
      ${this._tile('scale-balance', '#FAEEDA', '#854F0B', this._t('deviation'), `${dev >= 0 ? '+' : ''}${Math.round(dev)} mV`, slope != null ? this._t('per_day', { v: `${slope > 0 ? '+' : ''}${this._num(slope, 2)} mV` }) : '')}
      ${this._tile('thermometer', '#EAF3DE', '#3B6D11', this._t('temperature'), c.temps?.length ? `${this._num(c.temps[i], 1)} °C` : '–', '')}
      ${this._tile('sync', '#EEEDFE', '#3C3489', this._t('balancing'), c.balancing?.includes(i) ? this._t('yes') : this._t('no'), '')}
    </div>`;
    return this._box(this._cellName(c, i, b), '', `${tiles}<div class="grid2 tight"><div>${spark}</div><div class="diag ${c.drifting?.includes(i) ? 'bad' : ''}">${ehIcon(c.drifting?.includes(i) ? 'alert-outline' : 'check', 16)}<span>${ehEsc(diag)}</span></div></div>`);
  }

  _spreadChart(c) {
    const spreads = c.spread_30d || [];
    if (spreads.length < 2) return `<div class="hint">${ehEsc(this._t('learning_short'))}</div>`;
    const ahead = c.days_to_threshold != null ? Math.min(c.days_to_threshold, 60) : 0;
    const total = spreads.length - 1 + ahead;
    const maxv = Math.max(c.threshold_mv * 1.15, ...spreads);
    const X = (k) => 40 + (k / Math.max(total, 1)) * 1120;
    const Y = (v) => 110 - (v / maxv) * 96;
    let o = `<svg class="mini m" viewBox="0 0 1200 128" role="img" aria-label="${ehEsc(this._t('spread_trend'))}">`;
    o += `<line x1="40" x2="1160" y1="${Y(c.threshold_mv)}" y2="${Y(c.threshold_mv)}" stroke="${EH_RED}" stroke-dasharray="3 3"/><text class="svgt" x="44" y="${Y(c.threshold_mv) - 4}" style="fill:${EH_RED}">${ehEsc(this._t('threshold'))} ${c.threshold_mv} mV</text>`;
    o += `<path d="${spreads.map((v, k) => `${k ? 'L' : 'M'}${X(k).toFixed(1)} ${Y(v).toFixed(1)}`).join(' ')}" fill="none" stroke="#EF9F27" stroke-width="2"/>`;
    const lastK = spreads.length - 1;
    if (ahead) {
      const end = spreads[lastK] + ((c.threshold_mv - spreads[lastK]) * ahead) / c.days_to_threshold;
      o += `<path d="M${X(lastK).toFixed(1)} ${Y(spreads[lastK]).toFixed(1)} L${X(total).toFixed(1)} ${Y(end).toFixed(1)}" stroke="#EF9F27" stroke-width="1.6" stroke-dasharray="4 4"/><circle cx="${X(total)}" cy="${Y(end)}" r="4" fill="var(--card-background-color)" stroke="${EH_RED}" stroke-width="2"/>`;
      o += `<text class="svgt" x="${X(total) - 6}" y="${Y(end) + 16}" text-anchor="end">${ehEsc(this._t('in_days', { d: this._num(c.days_to_threshold, 0) }))}</text>`;
    }
    o += `<line x1="${X(lastK)}" x2="${X(lastK)}" y1="14" y2="110" stroke="var(--secondary-text-color)" stroke-width=".5" stroke-dasharray="3 3"/><line x1="40" x2="1160" y1="110" y2="110" stroke="var(--divider-color)"/>`;
    o += `<text class="svgt" x="40" y="124">−${ehEsc(this._t('days_30'))}</text><text class="svgt" x="${X(lastK)}" y="124" text-anchor="middle">${ehEsc(this._t('today'))}</text>`;
    return `${o}</svg>`;
  }

  // ---------- Losses
  _losses() {
    const d = this._data;
    const Lt = d.losses.today;
    const month = d.losses.month;
    const lostToday = Object.entries(Lt).filter(([k]) => !['potential', 'produced'].includes(k)).reduce((a, [, v]) => a + (v || 0), 0);
    const monthTotal = Object.values(month).reduce((a, v) => a + (v || 0), 0);
    const main = Object.entries(month).sort((a, b) => (b[1] || 0) - (a[1] || 0))[0];
    let o = `<div class="grid4">
      ${this._tile('flash-outline', '#FCEBEB', '#A32D2D', this._t('lost_today'), this._kwh(lostToday), Lt.potential ? this._pct(lostToday / Lt.potential) : '', EH_RED)}
      ${this._tile('calendar-month', '#FCEBEB', '#A32D2D', this._t('this_month_lost'), this._kwh(monthTotal), this._eur(d.losses.month_eur), EH_RED)}
      ${this._tile('check', '#EAF3DE', '#3B6D11', this._t('availability'), this._pct(d.losses.availability, 1), '', EH_GREEN)}
      ${this._tile('alert-outline', '#FCEBEB', '#A32D2D', this._t('main_cause'), main && main[1] > 0 ? ehEsc(this._t(`causes.${main[0]}`)) : this._t('none'), main && monthTotal ? this._pct(main[1] / monthTotal) : '', EH_RED)}
    </div>`;
    // cascade
    const steps = [['potential', Lt.potential, '#B4B2A9', true], ['clipping', -(Lt.clipping || 0), EH_RED], ['shading', -(Lt.shading || 0), '#F09595'], ['soiling', -(Lt.soiling || 0), '#F09595'], ['limitation', -(Lt.limitation || 0), '#F09595'], ['unavailability', -(Lt.unavailability || 0), '#F09595'], ['produced', Lt.produced, EH_AMBER, true]];
    const top = Lt.potential || 1;
    const floor = Math.max(0, Math.floor((Lt.produced || 0) * 0.85));
    const Y = (v) => 140 - ((v - floor) / Math.max(top - floor, 0.001)) * 120;
    let cur = 0;
    let svg = '<svg class="mini" viewBox="0 0 340 170" role="img" aria-label="Cascade">';
    steps.forEach(([key, v, col, total], i) => {
      const x = 8 + i * 47;
      let y0;
      let y1;
      if (total) {
        y0 = Y(v || 0);
        y1 = 140;
        cur = v || 0;
      } else {
        y0 = Y(cur);
        y1 = Y(cur + v);
        cur += v;
      }
      svg += `<rect x="${x}" y="${y0.toFixed(1)}" width="34" height="${Math.max(1.5, y1 - y0).toFixed(1)}" rx="3" fill="${col}"/>`;
      if (i < steps.length - 1) svg += `<line x1="${x + 34}" x2="${x + 47}" y1="${Y(cur).toFixed(1)}" y2="${Y(cur).toFixed(1)}" stroke="var(--secondary-text-color)" stroke-width=".6" stroke-dasharray="2 2"/>`;
      const label = total ? this._num(v || 0, 1) : v ? `−${this._num(-v, 1)}` : '0';
      svg += `<text class="svgt" x="${x + 17}" y="${(y0 - 5).toFixed(1)}" text-anchor="middle" ${total ? '' : `style="fill:${EH_RED}"`}>${label}</text><text class="svgt" x="${x + 17}" y="158" text-anchor="middle">${ehEsc(this._t(`causes_short.${key}`))}</text>`;
    });
    svg += '<path d="M2 136 l4 -4 l4 4 l4 -4" fill="none" stroke="var(--secondary-text-color)"/><line x1="6" x2="336" y1="140" y2="140" stroke="var(--divider-color)"/></svg>';
    // heatmap
    const hm = d.losses.heatmap;
    const hmax = Math.max(0.05, ...hm.flatMap((r) => r.h.map((v) => v || 0)));
    let heat = '<svg class="mini" viewBox="0 0 300 150" role="img" aria-label="Heatmap">';
    hm.forEach((r, di) => {
      r.h.forEach((v, k) => {
        const op = v ? Math.min(1, 0.15 + (0.85 * v) / hmax) : 0;
        heat += `<rect x="${34 + k * 36}" y="${6 + di * (128 / Math.max(hm.length, 1))}" width="34" height="${Math.max(128 / Math.max(hm.length, 1) - 0.7, 1)}" rx="1" fill="${op ? EH_RED : 'var(--divider-color)'}" ${op ? `fill-opacity="${op.toFixed(2)}"` : ''}><title>${r.d} ${10 + k}h · ${this._kwh(v)}</title></rect>`;
      });
    });
    for (let k = 0; k < 7; k++) heat += `<text class="svgt" x="${51 + k * 36}" y="146" text-anchor="middle">${10 + k}h</text>`;
    heat += '</svg>';
    o += `<div class="grid2">${this._box(this._t('cascade'), 'kWh', `${svg}<div class="hint">${ehEsc(this._t('axis_cut'))}</div>`)}${this._box(this._t('heatmap'), 'kWh', heat)}</div>`;
    // causes
    const CAUSES = ['clipping', 'shading', 'soiling', 'limitation', 'unavailability'];
    const colors = { clipping: EH_RED, shading: '#F09595', soiling: '#EF9F27', limitation: EH_VIOLET, unavailability: '#888780' };
    const stack = CAUSES.map((k) => [k, month[k] || 0]).filter(([, v]) => v > 0).map(([k, v]) => `<div style="flex:${v};background:${colors[k]}" title="${ehEsc(this._t(`causes.${k}`))}"></div>`).join('');
    const legend = CAUSES.map((k) => [k, month[k] || 0]).map(([k, v]) => `<span class="chip"><span class="sw" style="background:${colors[k]}"></span>${ehEsc(this._t(`causes.${k}`))} ${monthTotal ? this._pct(v / monthTotal) : '–'}</span>`).join('');
    o += this._box(this._t('causes_month'), this._kwh(monthTotal), `${stack ? `<div class="stack thin">${stack}</div>` : ''}<div class="legend">${legend}</div>`);
    o += this._box(this._t('events'), this._t('days_30'), this._events());
    return o;
  }

  _events() {
    const ev = this._data.losses.events || [];
    if (!ev.length) return `<div class="hint">${ehEsc(this._t('no_event'))}</div>`;
    const icon = { clipping: 'alert-outline', string_lagging: 'solar-panel', shading: 'weather-cloudy-alert', soiling: 'water-off', cell_drift: 'scale-balance', unavailability: 'power-plug-off-outline' };
    const statusColor = { recurring: ['#FCEBEB', '#A32D2D'], watch: ['#FAEEDA', '#854F0B'], resolved: ['#EAF3DE', '#3B6D11'] };
    const day = (s) => (s ? new Date(`${s}T12:00`).toLocaleDateString(this._locale, { day: 'numeric', month: 'short' }) : '');
    return ev
      .map((e) => {
        const [bg, fg] = statusColor[e.status];
        const title = this._t(`event.${e.kind}`, { unit: e.unit || '', name: e.name || '', battery: e.battery || '', cell: e.cell || '', from: e.start != null ? this._hm(e.start) : '', to: e.end != null ? this._hm(e.end) : '' });
        const bits = [];
        if (e.first && e.first !== e.last) bits.push(`${day(e.first)} → ${day(e.last)}`);
        else if (e.last) bits.push(day(e.last));
        if (e.days) bits.push(this._t(e.days === 1 ? 'one_day' : 'n_days', { n: e.days }));
        if (e.kwh != null) bits.push(this._kwh(e.kwh));
        if (e.relative != null) bits.push(`−${this._num((1 - e.relative) * 100, 0)} %`);
        if (e.loss != null) bits.push(`−${this._pct(e.loss, 1)}`);
        return `<div class="event"><div class="pa" style="background:${bg};color:${fg}">${ehIcon(icon[e.kind] || 'alert-outline', 18)}</div><div class="tt"><div class="a1">${ehEsc(title)}</div><div class="t3">${ehEsc(bits.join(' · '))}</div></div><span class="status" style="background:${bg};color:${fg}">${ehEsc(this._t(`status.${e.status}`))}</span></div>`;
      })
      .join('');
  }

  // ---------- Finances
  _calendar() {
    const cal = this._data.finances.calendar || [];
    if (!cal.length) return '';
    const max = Math.max(0.01, ...cal.map((c) => c.eur || 0));
    const first = new Date(`${cal[0].d}T12:00`);
    const heads = Array.from({ length: 7 }, (_v, i) => new Date(first.getTime() + i * 86400000).toLocaleDateString(this._locale, { weekday: 'narrow' }));
    const today = cal[cal.length - 1].d;
    const cells = cal
      .map((c) => {
        const k = c.eur != null ? c.eur / max : 0;
        const dt = new Date(`${c.d}T12:00`);
        return `<div class="cal${c.d === today ? ' today' : ''}" style="background:${c.eur != null ? `rgba(99,153,34,${(0.12 + 0.8 * k).toFixed(2)})` : 'var(--secondary-background-color)'};color:${k > 0.55 ? '#fff' : 'var(--primary-text-color)'}" title="${ehEsc(dt.toLocaleDateString(this._locale, { weekday: 'long', day: 'numeric', month: 'long' }))} · ${this._eur(c.eur)}"><span>${dt.getDate()}</span><b>${c.eur != null ? this._num(c.eur, c.eur < 10 ? 2 : 1) : ''}</b></div>`;
      })
      .join('');
    const legend = `<div class="legend"><span class="chip">${this._eur(0, 0)}</span><span class="calscale"></span><span class="chip">${this._eur(max)}</span></div>`;
    return `<div class="calgrid">${heads.map((h) => `<div class="calh">${ehEsc(h)}</div>`).join('')}${cells}</div>${legend}`;
  }

  _bill() {
    const b = this._data.finances.bill;
    if (!b) return '';
    const max = Math.max(1, b.month.without || 0, b.year.without || 0);
    const row = (label, p) => {
      const saved = (p.without || 0) - (p.with || 0);
      const scale = Math.max(p.without || 0, Math.abs(p.with || 0), 1);
      return `<div class="billrow"><div class="a1">${ehEsc(label)}</div>
        <div class="barrow"><span>${ehEsc(this._t('without_solar'))}</span><div class="meter"><div style="width:${((p.without || 0) / scale) * 100}%;background:#B4B2A9"></div></div><span>${this._eur(p.without, 0)}</span></div>
        <div class="barrow"><span>${ehEsc(this._t('with_solar'))}</span><div class="meter"><div style="width:${(Math.max(p.with || 0, 0) / scale) * 100}%;background:#639922"></div></div><span>${this._eur(p.with, 0)}</span></div>
        <div class="t3" style="color:${EH_GREEN}">${ehEsc(this._t('saved_amount', { v: this._eur(saved, 0) }))}${(p.with || 0) < 0 ? ` · ${ehEsc(this._t('credit'))}` : ''}</div></div>`;
    };
    return `${row(this._t('this_month'), b.month)}${row(this._t('months_12'), b.year)}<div class="hint">${ehEsc(this._t('bill_hint', { i: this._eur(this._data.finances.import_price, 4), e: this._eur(this._data.finances.export_price, 4) }))}</div>${max ? '' : ''}`;
  }

  _comparator() {
    const C = this._data.finances.comparator;
    if (!C) return '';
    if (!C.offers.length) return this._box(this._t('comparator'), '', `<div class="hint">${ehEsc(this._t('comparator_learning', { n: C.needed, d: C.days }))}</div>`);
    const tag = (r) => `<span class="pill small">${ehEsc(this._t(r.custom ? 'custom_offer' : r.regulated ? 'regulated' : 'market'))}</span>`;
    const rows = C.offers
      .map((r) => {
        const cur = r.key === C.current;
        const best = r.key === C.best;
        const delta = r.delta == null || cur ? '' : `<span style="color:${r.delta < 0 ? EH_GREEN : 'var(--secondary-text-color)'}">${r.delta > 0 ? '+' : ''}${this._eur(r.delta, 0)}</span>`;
        return `<tr class="${cur ? 'cur' : ''}"><td><div class="a1 oname">${best ? `<span style="color:${EH_GREEN}">${ehIcon('check', 14)}</span>` : ''}${ehEsc(r.name)}</div><div>${tag(r)}${cur ? ` <span class="pill small cur">${ehEsc(this._t('your_contract'))}</span>` : ''}</div></td><td class="num">${this._eur(r.avg_price, 4)}</td><td class="num">${this._eur(r.subscription, 0)}</td><td class="num"><b>${this._eur(r.total, 0)}</b><div class="t3">${delta}</div></td></tr>`;
      })
      .join('');
    const bestOffer = C.offers.find((r) => r.key === C.best);
    const verdict = !C.current ? this._t('no_contract') : C.best === C.current ? this._t('best_is_current') : this._t('best_saving', { name: bestOffer.name, v: this._eur(C.saving, 0) });
    const notes = [this._t('grid_info', { d: new Date(`${C.grid_date}T12:00`).toLocaleDateString(this._locale, { day: 'numeric', month: 'long', year: 'numeric' }) })];
    if (C.scale > 1.05) notes.push(this._t('scaled', { n: C.days }));
    if (C.colors < C.days) notes.push(this._t('colors_estimated', { n: C.days - C.colors }));
    const stale = C.grid_stale ? `<div class="hint" style="color:${EH_AMBER}">${ehIcon('alert-outline', 14)} ${ehEsc(this._t('grid_stale'))}</div>` : '';
    return this._box(
      this._t('comparator'),
      this._t('comparator_hint', { v: this._kwh(C.kwh) }),
      `<div class="verdict ${C.current && C.best !== C.current ? 'gain' : ''}">${ehEsc(verdict)}</div><table class="offers"><tr class="th"><td>${ehEsc(this._t('offer'))}</td><td class="num">${ehEsc(this._t('avg_price'))}</td><td class="num">${ehEsc(this._t('subscription'))}</td><td class="num">${ehEsc(this._t('total_year'))}</td></tr>${rows}</table>${stale}<div class="hint">${notes.map(ehEsc).join(' ')}</div>`,
    );
  }

  _finances() {
    const d = this._data;
    const F = d.finances;
    const share = F.share_paid ?? 0;
    const ring = `<svg width="140" height="140" viewBox="0 0 150 150" role="img" aria-label="${this._pct(share)}"><circle cx="75" cy="75" r="62" fill="none" stroke="var(--divider-color)" stroke-width="12"/><circle cx="75" cy="75" r="62" fill="none" stroke="#639922" stroke-width="12" stroke-linecap="round" transform="rotate(-90 75 75)" stroke-dasharray="${(389.6 * share).toFixed(1)} 390"/><text x="75" y="72" text-anchor="middle" class="svgth" style="font-size:22px">${this._pct(share)}</text><text x="75" y="92" text-anchor="middle" class="svgt">${ehEsc(this._t('amortised'))}</text></svg>`;
    const be = this._breakEven(this._rate);
    let o = `<div class="ringrow">${ring}<div class="grid2 tight">
      ${this._tile('piggy-bank-outline', '#EAF3DE', '#3B6D11', this._t('gained_since'), this._eur(F.since, 0), F.net_cost ? this._t('of_net_cost', { v: this._eur(F.net_cost, 0) }) : '', EH_GREEN)}
      ${this._tile('flag-outline', '#E6F1FB', '#185FA5', this._t('break_even'), be.label, be.sub, '#185FA5')}
      ${this._tile('calendar-month', '#EAF3DE', '#3B6D11', this._t('this_month'), this._eur(F.month), '')}
      ${this._tile('lightbulb-on-outline', '#EAF3DE', '#3B6D11', this._t('gain_20'), be.gain20 != null ? this._eur(be.gain20, 0) : '–', '', EH_GREEN)}
    </div></div>`;
    if (!F.net_cost) o += `<div class="hint">${ehEsc(this._t('no_cost'))}</div>`;
    else {
      o += this._box(this._t('projection'), this._t('net_cost', { v: this._eur(F.net_cost, 0) }), `<label class="slider">${ehEsc(this._t('price_rise'))}<input type="range" min="0" max="8" step="0.5" value="${this._rate}" data-rate><b>${ehEsc(this._t('per_year_short', { v: this._num(this._rate, 1) }))}</b></label>${be.svg}`);
    }
    const monthly = F.monthly;
    const mmax = Math.max(1, ...monthly.map((m) => m.eur));
    let bars = '<svg class="mini" viewBox="0 0 300 120" role="img" aria-label="Gains">';
    monthly.forEach((m, i) => {
      const h = (m.eur / mmax) * 90;
      bars += `<rect x="${10 + i * 24}" y="${100 - h}" width="16" height="${h}" rx="3" fill="#639922"><title>${m.m} · ${this._eur(m.eur)}</title></rect><text class="svgt" x="${18 + i * 24}" y="114" text-anchor="middle">${new Date(`${m.m}-01`).toLocaleString(this._hass?.locale?.language || 'en', { month: 'narrow' })}</text>`;
    });
    bars += '</svg>';
    const bd = F.breakdown;
    const total = (bd.direct || 0) + (bd.battery || 0) + (bd.export || 0);
    const row = (label, v, col) => `<div class="barrow"><span>${ehEsc(label)}</span><div class="meter"><div style="width:${total ? (v / total) * 100 : 0}%;background:${col}"></div></div><span>${this._eur(v, 0)}</span></div>`;
    o += `<div class="grid2">${this._box(this._t('gains_calendar'), this._t('weeks_6'), this._calendar())}${this._box(this._t('bill_title'), '', this._bill())}</div>`;
    o += this._comparator();
    o += `<div class="grid2">${this._box(this._t('gains_month'), '', bars)}${this._box(this._t('gains_from'), this._eur(total, 0), row(this._t('direct'), bd.direct, '#639922') + row(this._t('battery_restored'), bd.battery, EH_TEAL) + row(this._t('export'), bd.export, EH_BLUE))}</div>`;
    return o;
  }

  _breakEven(rate) {
    // The same projection as the integration (analytics/finance.py), redrawn here when the slider moves.
    const F = this._data.finances;
    if (!F.net_cost) return { label: '–', sub: '', svg: '', gain20: null };
    const age = F.age_years || 0;
    let total = F.since;
    let be = total >= F.net_cost ? 0 : null;
    const pts = [[age, total]];
    let invPaid = age >= F.inverter_lifetime_years;
    for (let m = 1; m <= Math.round((20 - age) * 12); m++) {
      const y = m / 12;
      total += (F.yearly / 12) * (1 + rate / 100) ** y * (1 - 0.005 * (age + y));
      if (!invPaid && age + y >= F.inverter_lifetime_years) {
        total -= F.inverter_replacement_cost;
        invPaid = true;
      }
      if (be == null && total >= F.net_cost) be = y;
      if (m % 3 === 0) pts.push([age + y, total]);
    }
    const ymax = Math.max(F.net_cost * 1.4, total * 1.05);
    const X = (a) => 40 + (a / 20) * 590;
    const Y = (v) => 125 - (Math.max(v, 0) / ymax) * 110;
    let svg = `<svg class="mini" viewBox="0 0 640 150" role="img" aria-label="Projection"><line x1="40" x2="630" y1="125" y2="125" stroke="var(--divider-color)"/><line x1="40" x2="630" y1="${Y(F.net_cost)}" y2="${Y(F.net_cost)}" stroke="${EH_BLUE}" stroke-dasharray="3 3"/>`;
    svg += `<path d="M${X(0)} 125 L${X(age)} ${Y(F.since)}" fill="none" stroke="#639922" stroke-width="2.2"/><path d="${pts.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(' ')}" fill="none" stroke="#639922" stroke-width="1.6" stroke-dasharray="4 4"/><circle cx="${X(age)}" cy="${Y(F.since)}" r="4.5" fill="#639922" stroke="var(--card-background-color)" stroke-width="2"/>`;
    if (be != null) svg += `<circle cx="${X(age + be)}" cy="${Y(F.net_cost)}" r="5" fill="var(--card-background-color)" stroke="${EH_BLUE}" stroke-width="2"/>`;
    if (F.inverter_lifetime_years > age) svg += `<line x1="${X(F.inverter_lifetime_years)}" x2="${X(F.inverter_lifetime_years)}" y1="20" y2="125" stroke="var(--secondary-text-color)" stroke-width=".5" stroke-dasharray="2 3"/><text class="svgt" x="${X(F.inverter_lifetime_years) + 4}" y="30">${ehEsc(this._t('inverter'))}</text>`;
    for (let y = 0; y <= 20; y += 4) svg += `<text class="svgt" x="${X(y)}" y="143" text-anchor="middle">${y}</text>`;
    svg += '</svg>';
    const when = be == null ? null : new Date(Date.now() + be * 365.25 * 86400000);
    return {
      label: when ? when.toLocaleDateString(this._hass?.locale?.language || 'en', { month: 'short', year: 'numeric' }) : '–',
      sub: be != null ? this._t('in_years', { v: this._num(be, 1) }) : '',
      svg,
      gain20: total - F.net_cost,
    };
  }

  // ---------- Settings
  _settingsTab() {
    const subs = ['sources', 'installation', 'tariffs', 'alerts', 'yaml'];
    const sub = subs.includes(this._sub) ? this._sub : 'sources';
    const nav = `<div class="subtabs">${subs.map((k) => `<button class="${sub === k ? 'on' : ''}" data-sub="${k}">${ehEsc(this._t(`subtabs.${k}`))}</button>`).join('')}<button class="round refresh-inline" data-action="refresh" aria-label="Refresh">${ehIcon('refresh', 16)}</button></div>`;
    this._snips = [];
    const body = { sources: this._setSources, installation: this._setInstallation, tariffs: this._setTariffs, alerts: this._setAlerts, yaml: this._setYaml }[sub].call(this);
    return nav + body;
  }

  _snip(yaml) {
    this._snips.push(yaml);
    return `<button class="copy" data-snip="${this._snips.length - 1}">${ehIcon('content-copy', 14)} ${ehEsc(this._t('copy_yaml'))}</button>`;
  }

  _setSources() {
    const d = this._data;
    let o = '';
    const sugg = d.suggestions || [];
    if (sugg.length) {
      o += this._box(this._t('suggestions'), `${sugg.length}`, sugg.map((s) => `<div class="sugg"><span class="pa sm" style="background:#EEEDFE;color:#3C3489">${ehIcon('lightbulb-on-outline', 14)}</span><div class="tt"><div class="a1">${ehEsc(this._t(`suggest.${s.kind}`, { bms: s.bms || '', battery: s.battery || '' }))}</div><div class="t3">${s.correlation != null ? ehEsc(this._t('correlation', { v: this._num(s.correlation, 2) })) : ''}</div></div>${this._snip(s.yaml)}</div>`).join(''));
    }
    const capIcon = { provided: 'check', estimated: 'function-variant', absent: 'minus' };
    const roleOrder = ['pv', 'storage', 'meter', 'forecast', 'weather', 'tariff', 'prefs'];
    const sources = [...d.sources].sort((a, b) => roleOrder.indexOf(a.role) - roleOrder.indexOf(b.role));
    let lastRole = null;
    const list = sources
      .map((src) => {
        const head = src.role !== lastRole ? `<div class="rolehead">${ehEsc(this._t(`source_role.${src.role}`))}</div>` : '';
        lastRole = src.role;
        const caps = Object.entries(src.capabilities).map(([k, v]) => `<span class="cap ${v}" title="${ehEsc(this._t(`capabilities.${v}`))}">${ehIcon(capIcon[v] || 'minus', 12)}${ehEsc(this._t(`cap.${k}`))}</span>`).join('');
        return `${head}<div class="src"><div class="tt"><div class="a1">${ehEsc(src.name)} ${src.status === 'beta' ? `<span class="pill small">${ehEsc(this._t('beta'))}</span>` : ''}</div><div>${caps}</div></div></div>`;
      })
      .join('');
    o += this._box(this._t('sources'), `${d.sources.length}`, `${list}<div class="legend"><span class="cap provided">${ehIcon('check', 12)}${ehEsc(this._t('capabilities.provided'))}</span><span class="cap estimated">${ehIcon('function-variant', 12)}${ehEsc(this._t('capabilities.estimated'))}</span><span class="cap absent">${ehIcon('minus', 12)}${ehEsc(this._t('capabilities.absent'))}</span></div>`);
    o += this._box(this._t('quality_24h'), this._t('quality_hint'), this._quality());
    const excl = Object.entries(d.excluded || {}).map(([e, why]) => `<tr><td>${ehEsc(this._t('excluded'))}</td><td><code class="muted">${ehEsc(e)}</code></td><td class="age">${ehEsc(this._t(`excluded_reason.${why}`))}</td></tr>`).join('');
    if (excl) o += this._box(this._t('excluded'), '', `<table class="roles">${excl}</table>`);
    return o;
  }

  _quality() {
    const q = this._data.quality || [];
    if (!q.length) return `<div class="hint">${ehEsc(this._t('learning_short'))}</div>`;
    const rows = q
      .map((r) => {
        const slots = r.slots.map((v) => `<i style="background:${v == null ? 'var(--divider-color)' : v >= 0.99 ? '#97C459' : v >= 0.5 ? '#EF9F27' : EH_RED}"></i>`).join('');
        const gaps = (r.gaps || []).map(([a, b]) => `${this._time(a)}–${this._time(b)}`).join(', ');
        const age = this._data.ages?.[r.entity];
        return `<div class="qrow"><div class="qname"><div class="a1">${ehEsc(this._roleLabel(r.role))}</div><code class="t3">${ehEsc(r.entity)}</code></div><div class="qbar">${slots}</div><div class="qval"><b style="color:${r.share >= 0.99 ? EH_GREEN : r.share >= 0.9 ? EH_AMBER : EH_RED}">${this._pct(r.share, 1)}</b><div class="t3">${gaps ? ehEsc(this._t('gaps', { v: gaps })) : age != null ? ehEsc(this._t('last_seen', { v: `${this._num(age, 0)} s` })) : ''}</div></div></div>`;
      })
      .join('');
    return `${rows}<div class="qrow axis"><span></span><div class="qaxis"><span>−24 h</span><span>−12 h</span><span>${ehEsc(this._t('now_short'))}</span></div><span></span></div>`;
  }

  _roleLabel(role) {
    if (role.includes('.')) {
      const [key, field] = role.split('.');
      const b = this._data.batteries.items.find((x) => x.key === key);
      return `${b ? b.name : key} · ${this._t(`cap.${field === 'power' ? 'power' : 'soc'}`)}`;
    }
    return this._t(`role.${role}`, {}, role);
  }

  _setInstallation() {
    const d = this._data;
    const s = this._settings || {};
    const roles = d.roles || {};
    const checks = [
      ['pv', !!(roles.pv_power || roles.pv_energy), roles.pv_power || roles.pv_energy, null],
      ['grid', !!(roles.grid_power || roles.grid_import_energy), roles.grid_power || roles.grid_import_energy, { link: '/config/energy' }],
      ['battery', d.batteries.items.length > 0, this._t('batteries_n', { n: d.batteries.items.length }), { yaml: 'energy_hub:\n  batteries:\n    house:\n      soc: sensor.battery_soc\n      power: sensor.battery_power\n      capacity_kwh: 10\n' }],
      ['forecast', !!roles.forecast_power, roles.forecast_power, { link: '/config/integrations/dashboard/add?domain=forecast_solar' }],
      ['planes', !d.kwp_estimated, d.kwp_estimated ? this._t('kwp_estimated') : this._t('kwp', { v: this._num(d.kwp, 1) }), { yaml: 'energy_hub:\n  planes:\n    - kwp: 3.0\n      tilt: 30\n      azimuth: 180\n' }],
      ['tariff', !!d.finances.net_cost, d.finances.net_cost ? this._eur(d.finances.net_cost, 0) : this._t('no_cost'), { yaml: 'energy_hub:\n  tariff:\n    import: 0.2016\n    export: 0.04\n  installation:\n    cost: 9000\n    subsidy: 0\n    commissioned: 2024-01-01\n' }],
    ];
    const okCount = checks.filter((c) => c[1]).length;
    const action = (a) => (a?.yaml ? this._snip(a.yaml) : a?.link ? `<a class="copy" href="${a.link}" target="_top">${ehIcon('chevron-right', 14)} ${ehEsc(this._t('open'))}</a>` : '');
    let o = `<div class="ringrow"><div class="tile col"><svg width="90" height="90" viewBox="0 0 90 90" role="img" aria-label="${okCount}/${checks.length}"><circle cx="45" cy="45" r="36" fill="none" stroke="var(--divider-color)" stroke-width="8"/><circle cx="45" cy="45" r="36" fill="none" stroke="#639922" stroke-width="8" stroke-linecap="round" transform="rotate(-90 45 45)" stroke-dasharray="${((226 * okCount) / checks.length).toFixed(0)} 227"/><text x="45" y="50" text-anchor="middle" class="svgth">${okCount}/${checks.length}</text></svg><div class="t1">${ehEsc(this._t('health_title'))}</div></div><section class="box">`;
    o += checks.map(([key, ok, detail, act]) => `<div class="check"><span class="pa sm" style="background:${ok ? '#EAF3DE' : '#FAEEDA'};color:${ok ? EH_GREEN : '#854F0B'}">${ehIcon(ok ? 'check' : 'alert-outline', 14)}</span><div class="tt"><div class="a1">${ehEsc(this._t(`checks.${key}`))}</div><div class="t3">${ehEsc(detail || this._t('check_missing'))}</div></div>${ok ? '' : action(act)}</div>`).join('');
    o += '</section></div>';
    o += this._box(this._t('schematic'), this._t('schematic_hint'), `${this._schematic()}${this._nodeDetail()}`);
    const planes = (s.planes || []).map((p, i) => `<tr><td>${ehEsc(this._t('plane_n', { n: i + 1 }))}</td><td>${this._num(p.kwp, 2)} kWp</td><td>${this._num(p.tilt, 0)}°</td><td>${this._num(p.azimuth, 0)}°</td></tr>`).join('');
    o += this._box(this._t('planes'), d.kwp_estimated ? this._t('estimated') : this._t('kwp', { v: this._num(d.kwp, 2) }), `${planes ? `<table class="roles"><tr><th></th><th>${ehEsc(this._t('power'))}</th><th>${ehEsc(this._t('tilt'))}</th><th>${ehEsc(this._t('azimuth'))}</th></tr>${planes}</table>` : `<div class="hint">${ehEsc(this._t('kwp_estimated'))}</div>`}<table class="roles"><tr><td>${ehEsc(this._t('inverter_max_short'))}</td><td>${this._kw(d.inverter_max_kw)}</td></tr><tr><td>${ehEsc(this._t('export_limit'))}</td><td>${d.export_limit_kw ? this._kw(d.export_limit_kw) : '–'}</td></tr></table>`);
    o += this._reference();
    return o;
  }

  _reference() {
    const R = this._data.reference || {};
    const order = [
      ['measured', R.irradiance],
      ['forecast', R.forecast],
      ['weather', R.weather],
      ['clearsky', null],
    ];
    const used = R.source || 'clearsky';
    const rows = order
      .map(([kind, entity]) => {
        const on = kind === used;
        const avail = kind === 'clearsky' || !!entity;
        return `<div class="check"><span class="pa sm" style="background:${on ? '#EAF3DE' : 'var(--secondary-background-color)'};color:${on ? EH_GREEN : 'var(--secondary-text-color)'}">${ehIcon(on ? 'check' : avail ? 'minus' : 'close', 14)}</span><div class="tt"><div class="a1">${ehEsc(this._t(`reference_kind.${kind}`))}</div><div class="t3">${entity ? `<code>${ehEsc(entity)}</code> · ` : ''}${kind === 'clearsky' && !on ? '' : ehEsc(this._t(`reference_hint.${kind}`))}</div></div></div>`;
      })
      .join('');
    return this._box(this._t('reference'), this._t(`reference_kind.${used}`), `${rows}${R.irradiance ? '' : this._snip('energy_hub:\n  entities:\n    irradiance: sensor.solar_radiation\n  weather: weather.home\n')}`);
  }

  _schematic() {
    const d = this._data;
    const L = d.layout || {};
    const items = d.batteries.items;
    const dc = items.filter((b) => b.coupling === 'dc');
    const ac = items.filter((b) => b.coupling !== 'dc');
    const sel = this._node;
    const node = (key, x, y, w, h, title, sub, color, icon) => `<g class="node${sel === key ? ' on' : ''}" data-node="${ehEsc(key)}" tabindex="0" role="button"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="var(--card-background-color)" stroke="${color}" stroke-width="${sel === key ? 2.5 : 1.4}"/><circle cx="${x + 20}" cy="${y + h / 2}" r="13" fill="${color}" fill-opacity=".14"/><g transform="translate(${x + 11} ${y + h / 2 - 9}) scale(.75)" style="color:${color}"><path fill="currentColor" d="${EH_ICONS[icon]}"/></g><text class="svgth" x="${x + 40}" y="${y + h / 2 - 3}" style="font-size:12px">${ehEsc(title)}</text><text class="svgt" x="${x + 40}" y="${y + h / 2 + 12}" style="font-size:10px">${ehEsc(sub)}</text></g>`;
    // DC side on the left: the panels and the DC-coupled batteries feed the inverter
    const dcBottom = 110 + Math.max(dc.length, 0) * 62;
    const busY = Math.max(dcBottom, 150) + 10;
    const H = busY + 80;
    let o = `<svg class="schema" viewBox="0 0 680 ${H}" role="img" aria-label="${ehEsc(this._t('schematic'))}">`;
    o += '<path d="M180 49 H250" stroke="#EF9F27" stroke-width="3"/>';
    for (let i = 0; i < dc.length; i++) o += `<path d="M180 ${135 + i * 62} H215 V60 H250" fill="none" stroke="#EF9F27" stroke-width="3"/>`;
    o += '<text class="svgt" x="215" y="42" text-anchor="middle" style="font-size:10px;fill:#BA7517">DC</text>';
    if (L.forecast) o += '<path d="M470 49 H420" fill="none" stroke="var(--secondary-text-color)" stroke-dasharray="3 3"/>';
    // AC side below: AC-coupled batteries, the home and the meter on one bus
    const acRow = ac.map((b) => [`battery:${b.key}`, b.name, `AC · ${this._num(b.capacity_kwh, 1)} kWh`, EH_TEAL, 'battery-charging']);
    acRow.push(['home', this._t('home'), d.roles?.load_power ? this._t('measured_short') : this._t('computed'), EH_GREEN, 'home-lightning-bolt-outline']);
    acRow.push(['meter', L.meter || this._t('grid'), d.export_limit_kw ? this._t('limit_kw', { v: this._kw(d.export_limit_kw) }) : this._t('grid'), EH_BLUE, 'transmission-tower']);
    const w = Math.min(160, (640 - 10 * (acRow.length - 1)) / acRow.length);
    const xs = acRow.map((_r, i) => 20 + i * (w + 10));
    o += `<path d="M335 78 V${busY}" stroke="#378ADD" stroke-width="3"/><path d="M${Math.min(xs[0] + w / 2, 335)} ${busY} H${Math.max(xs[xs.length - 1] + w / 2, 335)}" stroke="#378ADD" stroke-width="3"/><text class="svgt" x="343" y="${busY - 8}" style="font-size:10px;fill:#185FA5">AC</text>`;
    for (const x of xs) o += `<path d="M${x + w / 2} ${busY} V${busY + 20}" stroke="#378ADD" stroke-width="3"/>`;
    o += node('pv', 20, 24, 160, 50, this._t('solar'), `${(L.strings || []).length} strings${L.units ? ` · ${L.units} ${this._t('panels')}` : ''}`, EH_AMBER, 'solar-panel');
    o += node('inverter', 250, 24, 170, 54, L.inverter || this._t('inverter_cap'), `DC → AC · ${this._kw(d.inverter_max_kw)}`, EH_AMBER, 'flash-outline');
    if (L.forecast) o += node('forecast', 470, 24, 190, 50, this._t('forecast'), L.forecast, '#888780', 'weather-cloudy-alert');
    dc.forEach((b, i) => {
      o += node(`battery:${b.key}`, 20, 110 + i * 62, 160, 50, b.name, `DC · ${this._num(b.capacity_kwh, 1)} kWh`, EH_TEAL, 'battery-charging');
    });
    acRow.forEach(([key, t, s2, c, ic], i) => {
      o += node(key, xs[i], busY + 20, w, 50, t, s2, c, ic);
    });
    return `${o}</svg>`;
  }

  _nodeDetail() {
    const key = this._node;
    if (!key) return `<div class="hint">${ehEsc(this._t('schematic_click'))}</div>`;
    const d = this._data;
    const s = this._settings || {};
    const roles = d.roles || {};
    const capIcon = { provided: 'check', estimated: 'function-variant', absent: 'minus' };
    const capsOf = (role) => {
      const src = d.sources.find((x) => x.role === role);
      return src ? Object.entries(src.capabilities).map(([k, v]) => `<span class="cap ${v}">${ehIcon(capIcon[v] || 'minus', 12)}${ehEsc(this._t(`cap.${k}`))}</span>`).join('') : '';
    };
    const ents = (list) => `<table class="roles">${list.filter(([, e]) => e).map(([r, e]) => `<tr><td>${ehEsc(r)}</td><td><code>${ehEsc(e)}</code></td><td class="age">${d.ages?.[e] != null ? `${this._num(d.ages[e], 0)} s` : ''}</td></tr>`).join('')}</table>`;
    let title = '';
    let body = '';
    if (key === 'pv' || key === 'inverter') {
      title = key === 'pv' ? this._t('solar') : d.layout?.inverter || this._t('inverter_cap');
      body = `<div>${capsOf('pv')}</div>${ents([['pv_power', roles.pv_power], ['pv_energy', roles.pv_energy]])}${key === 'pv' ? `<div class="t3">${ehEsc((d.layout?.strings || []).join(' · '))}</div>` : ''}`;
    } else if (key === 'forecast') {
      title = d.layout?.forecast || this._t('forecast');
      body = `<div>${capsOf('forecast')}</div>${ents([['forecast_power', roles.forecast_power], ['forecast_energy_today', roles.forecast_energy_today]])}`;
    } else if (key === 'meter') {
      title = d.layout?.meter || this._t('grid');
      body = `<div>${capsOf('meter')}</div>${ents([['grid_power', roles.grid_power], ['grid_import_energy', roles.grid_import_energy], ['grid_export_energy', roles.grid_export_energy]])}`;
    } else if (key === 'home') {
      title = this._t('home');
      body = roles.load_power ? ents([['load_power', roles.load_power]]) : `<div class="hint">${ehEsc(this._t('home_computed'))}</div>`;
    } else if (key.startsWith('battery:')) {
      const b = d.batteries.items.find((x) => `battery:${x.key}` === key);
      const cfg = (s.batteries || []).find((x) => x.key === b?.key) || {};
      const src = d.sources.find((x) => x.platform === b?.platform);
      title = b ? b.name : '';
      body = `<div>${src ? Object.entries(src.capabilities).map(([k, v]) => `<span class="cap ${v}">${ehIcon(capIcon[v] || 'minus', 12)}${ehEsc(this._t(`cap.${k}`))}</span>`).join('') : ''}</div>${ents([['soc', cfg.soc], ['power', cfg.power]])}<div class="t3">${ehEsc(this._t(`coupling.${b?.coupling}`))} · ${this._num(b?.capacity_kwh, 1)} kWh · ${ehEsc(this._t('reserve', { v: `${this._num(b?.reserve, 0)} %` }))}${cfg.cells ? ` · ${this._t('n_cells', { n: cfg.cells })}` : ''}</div>`;
    }
    return `<div class="nodedetail"><div class="a1">${ehEsc(title)}</div>${body}</div>`;
  }

  _setTariffs() {
    const d = this._data;
    const s = this._settings || {};
    const t = s.tariff || {};
    const inst = s.installation || {};
    const F = d.finances;
    const row = (label, value) => `<tr><td>${ehEsc(label)}</td><td>${value}</td></tr>`;
    const C = F.comparator || {};
    const offerName = (C.offers || []).find((r) => r.key === C.contract)?.name || C.contract;
    const assumed = (flag) => (flag ? ` <span class="pill small">${ehEsc(this._t('assumed'))}</span>` : '');
    const ent = (role) => (d.roles?.[role] ? `<code>${ehEsc(d.roles[role])}</code>` : '–');
    let o = this._box(
      this._t('contract_box'),
      C.contract_source ? this._t(`contract_source.${C.contract_source}`) : '',
      `<table class="roles">${row(this._t('contract'), C.contract ? ehEsc(offerName) : ehEsc(this._t('no_contract')))}${row(this._t('subscribed_power'), `${C.kva ?? '–'} kVA${assumed(C.kva_assumed)}`)}${row(this._t('offpeak_hours'), `${ehEsc(C.offpeak || '–')}${assumed(C.offpeak_assumed)}`)}${row(this._t('price_now'), `${this._eur(F.import_price, 4)} /kWh`)}${row(this._t('price_entity'), ent('tariff_price'))}${row(this._t('color_entity'), ent('tariff_color'))}</table>${this._snip(`energy_hub:\n  tariff:\n    contract: ${C.contract || 'hphc'}\n    kva: ${C.kva || 6}\n    offpeak: "${C.offpeak || '22:00-06:00'}"\n`)}`,
    );
    o += this._box(this._t('tariff_box'), d.currency, `<table class="roles">${C.contract ? '' : row(this._t('import_price'), `${this._eur(t.import ?? F.import_price, 4)} /kWh`)}${row(this._t('export_price'), `${this._eur(t.export ?? F.export_price, 4)} /kWh`)}</table>${this._snip(`energy_hub:\n  tariff:\n    import: ${t.import ?? F.import_price}\n    export: ${t.export ?? F.export_price}\n    currency: ${d.currency}\n`)}`);
    o += this._box(this._t('installation_box'), '', `<table class="roles">${row(this._t('cost'), inst.cost != null ? this._eur(inst.cost, 0) : '–')}${row(this._t('subsidy'), inst.subsidy != null ? this._eur(inst.subsidy, 0) : '–')}${row(this._t('net_cost_label'), F.net_cost != null ? this._eur(F.net_cost, 0) : '–')}${row(this._t('commissioned'), inst.commissioned ? new Date(`${inst.commissioned}T12:00`).toLocaleDateString(this._locale, { day: 'numeric', month: 'long', year: 'numeric' }) : '–')}${row(this._t('inverter_replacement'), `${this._eur(F.inverter_replacement_cost, 0)} · ${this._t('after_years', { v: this._num(F.inverter_lifetime_years, 0) })}`)}</table>${this._snip(`energy_hub:\n  installation:\n    cost: ${inst.cost ?? 9000}\n    subsidy: ${inst.subsidy ?? 0}\n    commissioned: ${inst.commissioned ?? '2024-01-01'}\n`)}`);
    return o + `<div class="hint">${ehEsc(this._t('yaml_wins'))}</div>`;
  }

  _setAlerts() {
    const d = this._data;
    const s = this._settings || {};
    const active = new Set(d.alerts.map((a) => a.kind));
    const kinds = ['clipping', 'string_lagging', 'shading', 'soiling', 'cell_drift', 'battery_exchange', 'stale'];
    const rows = kinds.map((k) => `<div class="check"><span class="pa sm" style="background:${active.has(k) ? '#FCEBEB' : '#EAF3DE'};color:${active.has(k) ? '#A32D2D' : EH_GREEN}">${ehIcon(active.has(k) ? 'alert-outline' : 'check', 14)}</span><div class="tt"><div class="a1">${ehEsc(this._t(`alert_kind.${k}`))}</div><div class="t3">${ehEsc(this._t(`alert_rule.${k}`))}</div></div><span class="status" style="background:${active.has(k) ? '#FCEBEB' : 'var(--secondary-background-color)'};color:${active.has(k) ? '#A32D2D' : 'var(--secondary-text-color)'}">${ehEsc(this._t(active.has(k) ? 'active' : 'inactive'))}</span></div>`).join('');
    let o = this._box(this._t('alert_rules'), this._t('active_n', { n: active.size }), rows);
    o += this._box(this._t('notifications'), '', `<table class="roles"><tr><td>${ehEsc(this._t('notify_target'))}</td><td>${s.notify ? `<code>${ehEsc(s.notify)}</code>${s.notify_auto ? ` <span class="pill small">${ehEsc(this._t('detected'))}</span>` : ''}` : ehEsc(this._t('no_notify'))}</td></tr><tr><td>${ehEsc(this._t('event_name'))}</td><td><code>energy_hub_alert</code></td></tr><tr><td>${ehEsc(this._t('frequency'))}</td><td>${ehEsc(this._t('once_a_day'))}</td></tr></table>${s.notify ? '' : this._snip('energy_hub:\n  notify: notify.mobile_app_phone\n')}`);
    return o;
  }

  _setYaml() {
    const s = this._settings;
    if (!s?.yaml) return `<div class="hint">${ehEsc(this._t('loading'))}</div>`;
    return this._box(this._t('yaml'), s.yaml_configured ? this._t('yaml_in_use') : this._t('yaml_detected'), `${this._snip(s.yaml)}<pre>${ehEsc(s.yaml)}</pre>`);
  }

  // ---------- render
  _render() {
    if (!this.shadowRoot) return;
    let body;
    if (this._error) body = `<div class="empty">${ehEsc(this._t('not_loaded'))}<br><small>${ehEsc(this._error)}</small></div>`;
    else if (!this._data) body = `<div class="empty">${ehEsc(this._t('loading'))}</div>`;
    else {
      const content = { overview: this._overview, production: this._production, batteries: this._batteries, losses: this._losses, finances: this._finances, settings: this._settingsTab }[this._tab] || this._overview;
      body = `${this._header()}<main>${content.call(this)}</main>`;
    }
    const scroll = this.shadowRoot.querySelector('.scroll');
    const top = scroll?.scrollTop || 0;
    this.shadowRoot.innerHTML = `<style>${EH_CSS}</style><div class="scroll ${this._narrow ? 'narrow' : ''}">${body}</div>`;
    const sc = this.shadowRoot.querySelector('.scroll');
    sc.scrollTop = top;
    sc.addEventListener('scroll', () => {
      const c = sc.scrollTop > 24;
      if (c !== this._collapsed) {
        this._collapsed = c;
        this.shadowRoot.querySelector('.banner')?.classList.toggle('collapsed', c);
      }
    }, { passive: true });
    this._bind();
  }

  _bind() {
    const root = this.shadowRoot;
    for (const el of root.querySelectorAll('[data-tab]')) el.addEventListener('click', () => this._setTab(el.dataset.tab));
    for (const el of root.querySelectorAll('[data-battery]')) {
      el.addEventListener('click', () => {
        this._battery = el.dataset.battery;
        this._cell = null;
        this._render();
      });
    }
    for (const el of root.querySelectorAll('[data-cell]')) {
      el.addEventListener('click', () => {
        this._cell = Number(el.dataset.cell);
        this._render();
      });
    }
    for (const el of root.querySelectorAll('[data-cellmetric]')) {
      el.addEventListener('click', () => {
        this._cellMetric = el.dataset.cellmetric;
        this._render();
      });
    }
    for (const el of root.querySelectorAll('[data-period]')) {
      el.addEventListener('click', () => {
        this._period = el.dataset.period;
        this._render();
      });
    }
    for (const el of root.querySelectorAll('[data-sub]')) {
      el.addEventListener('click', () => {
        this._sub = el.dataset.sub;
        this._render();
      });
    }
    for (const el of root.querySelectorAll('[data-node]')) {
      const pick = () => {
        this._node = this._node === el.dataset.node ? null : el.dataset.node;
        this._render();
      };
      el.addEventListener('click', pick);
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') pick();
      });
    }
    for (const el of root.querySelectorAll('[data-snip]')) {
      el.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(this._snips[Number(el.dataset.snip)]);
          el.textContent = this._t('copied');
        } catch (_err) {
          // clipboard unavailable (http)
        }
      });
    }
    root.querySelector('[data-rate]')?.addEventListener('input', (e) => {
      this._rate = Number(e.target.value);
      this._render();
    });
    for (const el of root.querySelectorAll('[data-action="refresh"]')) el.addEventListener('click', async () => {
      try {
        this._data = await this._hass.callWS({ type: 'energy_hub/snapshot' });
        this._render();
      } catch (_err) {
        // kept as is
      }
    });
    root.querySelector('[data-action="menu"]')?.addEventListener('click', () => this.dispatchEvent(new Event('hass-toggle-menu', { bubbles: true, composed: true })));
    this._bindCurve();
  }

  _bindCurve() {
    const svg = this.shadowRoot.querySelector('svg.curve');
    const meta = this._curveMeta;
    if (!svg || !meta) return;
    const hit = svg.querySelector('.hit');
    const hov = svg.querySelector('.hov');
    const tip = this.shadowRoot.querySelector('.tip');
    hit.addEventListener('mousemove', (ev) => {
      const r = svg.getBoundingClientRect();
      const sx = ((ev.clientX - r.left) * 680) / r.width;
      const t = meta.t0 + ((sx - meta.x0) / (meta.x1 - meta.x0)) * (meta.t1 - meta.t0);
      let best = null;
      for (const row of meta.rows) if (!best || Math.abs(row.t - t) < Math.abs(best.t - t)) best = row;
      if (!best) return;
      const x = meta.x0 + ((best.t - meta.t0) / (meta.t1 - meta.t0)) * (meta.x1 - meta.x0);
      hov.setAttribute('x1', x);
      hov.setAttribute('x2', x);
      hov.style.display = '';
      const clipped = this._data.inverter_max_kw && best.exp != null && best.pv != null && best.exp > this._data.inverter_max_kw && best.pv >= 0.97 * this._data.inverter_max_kw;
      tip.innerHTML = `<b>${this._time(best.t)}</b><br>${ehEsc(this._t('production'))} ${this._kw(best.pv)}<br>${ehEsc(this._t('forecast'))} ${this._kw(best.exp)}<br>${ehEsc(this._t('consumption'))} ${this._kw(best.load)}${best.soc != null ? `<br>${ehEsc(this._t('battery'))} ${this._num(best.soc, 0)} %` : ''}${clipped ? `<br><span style="color:${EH_RED}">${ehEsc(this._t('clipped', { v: this._kw(best.exp - best.pv) }))}</span>` : ''}`;
      tip.style.display = 'block';
      const px = (x * r.width) / 680;
      tip.style.left = `${px > r.width / 2 ? px - tip.offsetWidth - 10 : px + 10}px`;
    });
    hit.addEventListener('mouseleave', () => {
      hov.style.display = 'none';
      tip.style.display = 'none';
    });
  }
}

const EH_CSS = `
:host{display:block;height:100%;background:var(--primary-background-color);color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,Roboto,sans-serif)}
.scroll{height:100%;overflow-y:auto;overflow-x:hidden}
.ic{flex-shrink:0;display:block}
.banner{position:sticky;top:0;z-index:3;height:90px;overflow:hidden;transition:height .2s;background:var(--sky)}
.banner::before{content:'';position:absolute;left:0;right:0;bottom:0;height:6px;background:var(--ground)}
.banner .scene{position:absolute;inset:0;width:100%;height:100%}
.banner .bar{position:relative;display:flex;align-items:center;gap:12px;height:90px;padding:0 14px;transition:height .2s}
.banner .badge{width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.banner .titles{min-width:0}
.banner .title{font-size:18px;font-weight:500;color:var(--txt);display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.banner .sub{font-size:12px;color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pill{font-size:11px;font-weight:400;padding:2px 8px;border-radius:10px;white-space:nowrap}
.pill.demo{background:#EEEDFE;color:#3C3489}
.pill.small{background:var(--secondary-background-color);color:var(--secondary-text-color);font-size:10px;padding:1px 6px}
.round{width:32px;height:32px;border-radius:50%;border:0;background:var(--btn);color:var(--txt);display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;margin-left:auto}
.round.menu{display:none;margin-left:0}
.narrow .round.menu{display:flex}
.tabpills{display:none;gap:4px;margin-left:auto}
.tabpill{width:30px;height:30px;border-radius:50%;border:0;background:var(--btn);color:var(--sub);display:flex;align-items:center;justify-content:center;cursor:pointer;position:relative}
.tabpill.on{background:#FAC775;color:#633806}
.dot{position:absolute;top:2px;right:2px;width:7px;height:7px;border-radius:4px;background:${EH_RED}}
.dot.inline{position:static;display:inline-block;margin-left:4px;vertical-align:6px}
.banner.collapsed{height:52px;box-shadow:0 1px 0 var(--divider-color)}
.banner.collapsed .scene{opacity:0}
.banner.collapsed .bar{height:52px}
.banner.collapsed .badge{width:32px;height:32px}
.banner.collapsed .sub{display:none}
.banner.collapsed .title{font-size:14px}
.banner.collapsed .tabpills{display:flex}
.banner.collapsed .round:not(.menu){margin-left:0}
.banner.collapsed::before{height:3px}
.tabs{display:flex;gap:18px;padding:0 16px;border-bottom:1px solid var(--divider-color);background:var(--card-background-color);overflow-x:auto}
.tab{border:0;background:none;padding:11px 0;font:inherit;font-size:14px;color:var(--secondary-text-color);cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent}
.tab.on{color:var(--primary-text-color);font-weight:500;border-bottom-color:${EH_AMBER}}
main{padding:12px 16px 32px;max-width:1100px;margin:0 auto;display:flex;flex-direction:column;gap:12px}
.flow{width:100%;max-width:760px;margin:0 auto;display:block}
.node{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:14px;padding:8px 10px;display:flex;gap:9px;align-items:center;height:100%;box-sizing:border-box}
.pa{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.pa.sm{width:24px;height:24px}
.tt{min-width:0;flex:1}
.t1{font-size:11px;color:var(--secondary-text-color);line-height:1.25}
.t2{font-size:16px;font-weight:500;line-height:1.3}
.t3{font-size:11px;line-height:1.25;color:var(--secondary-text-color)}
.soc{height:4px;border-radius:2px;background:var(--divider-color);margin-top:4px}
.soc div{height:4px;border-radius:2px;background:${EH_TEAL}}
.svgt{font-size:12px;fill:var(--secondary-text-color)}
.svgth{font-size:14px;font-weight:500;fill:var(--primary-text-color)}
.svgt.dark,.svgth.dark{fill:#412402}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.kpi{background:var(--secondary-background-color);border-radius:10px;padding:9px 11px}
.k1{font-size:12px;color:var(--secondary-text-color)}
.k2{font-size:19px;font-weight:500}
.k3{font-size:11px;color:var(--secondary-text-color)}
.box{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:12px;padding:10px 12px}
.hd{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.box h3{margin:0;font-size:14px;font-weight:500}
.hint{font-size:11px;color:var(--secondary-text-color)}
.legend{display:flex;flex-wrap:wrap;gap:6px 12px;margin:2px 0 6px}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--secondary-text-color)}
.sw{width:10px;height:10px;border-radius:3px;display:inline-block}
.curvewrap{position:relative}
.curve{width:100%;display:block}
.curve .svgt{font-size:9px}
.tip{position:absolute;top:8px;pointer-events:none;background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:8px;padding:6px 9px;font-size:12px;line-height:1.5;min-width:130px;display:none;box-shadow:0 2px 8px rgba(0,0,0,.12)}
.tip b{font-weight:500}
.grid-auto{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px}
.grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.grid2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}
.grid2.tight{gap:8px}
.tile{background:var(--secondary-background-color);border-radius:12px;padding:9px 10px;display:flex;gap:9px;align-items:center;min-width:0}
.tile.col{flex-direction:column;justify-content:center;text-align:center}
.alert,.bcard{background:var(--secondary-background-color);border:0;border-radius:12px;padding:10px 12px;display:flex;gap:10px;align-items:center;cursor:pointer;font:inherit;color:inherit;text-align:left;width:100%}
.bcard{background:var(--card-background-color);border:1px solid var(--divider-color)}
.bcard.on{border:2px solid ${EH_TEAL};padding:9px 11px}
.a1{font-size:13px;font-weight:500}
.a2{font-size:12px}
.muted{color:var(--secondary-text-color);font-weight:400}
.brand{display:inline-block;font-size:10px;padding:1px 6px;border-radius:8px;background:var(--secondary-background-color);color:var(--secondary-text-color);margin-top:3px}
.roof{width:100%;max-width:640px;margin:0 auto;display:block}
.mini{width:100%;display:block}
.mini .svgt{font-size:8px}
.mini.m .svgt{font-size:11px}
.barrow{display:grid;grid-template-columns:110px minmax(0,1fr) 120px;gap:8px;align-items:center;font-size:12px;margin:6px 0}
.barrow span:last-child{text-align:right}
.meter{height:10px;border-radius:5px;background:var(--secondary-background-color);overflow:hidden}
.meter div{height:10px}
.stack{display:flex;height:22px;border-radius:6px;overflow:hidden;font-size:11px;color:#fff}
.stack div{display:flex;align-items:center;padding-left:6px;white-space:nowrap;overflow:hidden}
.stack.thin{height:14px}
.seg{display:inline-flex;background:var(--secondary-background-color);border-radius:8px;padding:2px}
.seg button{font:inherit;font-size:12px;padding:3px 10px;border-radius:6px;color:var(--secondary-text-color);background:none;border:0;cursor:pointer}
.seg button.on{background:var(--card-background-color);color:var(--primary-text-color)}
.cells{display:grid;gap:3px;margin:4px 0 8px}
.cell{height:34px;border-radius:5px;border:0;font:inherit;font-size:10px;color:var(--primary-text-color);cursor:pointer;padding:0}
.cell.sel{outline:2px solid var(--primary-text-color);outline-offset:1px}
.ringrow{display:grid;grid-template-columns:150px minmax(0,1fr);gap:12px;align-items:center}
.slider{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--secondary-text-color);margin-bottom:6px}
.slider b{font-weight:500;color:var(--primary-text-color)}
.check{display:flex;gap:9px;align-items:center;padding:6px 0;border-top:1px solid var(--divider-color)}
.check:first-child{border-top:0}
.src{padding:8px 0;border-top:1px solid var(--divider-color)}
.src:first-of-type{border-top:0}
.cap{display:inline-flex;align-items:center;gap:3px;font-size:11px;padding:1px 7px;border-radius:8px;margin:3px 4px 0 0}
.cap.provided{background:#EAF3DE;color:#27500A}
.cap.estimated{background:#FAEEDA;color:#633806}
.cap.absent{background:var(--secondary-background-color);color:var(--secondary-text-color)}
.roles{width:100%;border-collapse:collapse;font-size:12px}
.offers{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}
.offers td{padding:6px 4px;border-top:1px solid var(--divider-color);vertical-align:top}
.offers tr.th td{border-top:0;color:var(--secondary-text-color);font-size:11px}
.offers tr.cur td{background:var(--secondary-background-color)}
.offers .oname{display:flex;align-items:center;gap:4px}
.offers td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.pill.small.cur{background:#E6F1FB;color:#185FA5}
.verdict{font-size:13px;padding:8px 10px;border-radius:8px;background:var(--secondary-background-color)}
.verdict.gain{background:#EAF3DE;color:#27500A}
.roles td{padding:5px 4px;border-top:1px solid var(--divider-color);vertical-align:top}
.roles td.age{text-align:right;color:var(--secondary-text-color);white-space:nowrap}
code,pre{font-family:var(--code-font-family,ui-monospace,monospace)}
pre{background:var(--secondary-background-color);border-radius:8px;padding:10px 12px;font-size:12px;overflow-x:auto;margin:6px 0 0}
.copy{font:inherit;font-size:12px;border:1px solid var(--divider-color);background:var(--card-background-color);color:var(--primary-text-color);border-radius:8px;padding:3px 10px;cursor:pointer;display:inline-flex;align-items:center;gap:4px}
.empty{padding:40px 16px;text-align:center;color:var(--secondary-text-color)}
.pill .short{display:none}
.banner.collapsed .pill .long{display:none}
.banner.collapsed .pill .short{display:inline}
.banner.collapsed .pill.demo{display:none}
.bell{position:relative}
.bell .count{position:absolute;top:-3px;right:-3px;min-width:16px;height:16px;border-radius:8px;background:${EH_RED};color:#fff;font-size:10px;font-weight:500;display:flex;align-items:center;justify-content:center;padding:0 4px;box-sizing:border-box}
.round.bell{margin-left:auto}
.round.refresh{margin-left:0}
.banner.collapsed .round.bell{margin-left:0}
.refresh-inline{display:none;margin-left:auto;--btn:var(--secondary-background-color)}
.hd.sub{margin-bottom:4px}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.battrow{display:grid;grid-template-columns:150px minmax(0,1fr);gap:14px;align-items:center}
.bbwrap{display:flex;flex-direction:column;align-items:center;gap:2px;text-align:center}
.bigbatt{width:110px;height:auto}
.cellrow{display:grid;grid-template-columns:70px minmax(0,1fr);gap:8px;align-items:center}
.cellrow .cells{margin:2px 0}
.rowlab{font-size:11px;color:var(--secondary-text-color)}
.cell{position:relative}
.cell.drift{outline:2px solid ${EH_RED};outline-offset:-2px}
.baldot{position:absolute;top:3px;right:3px;width:6px;height:6px;border-radius:3px;background:${EH_VIOLET}}
.baldot.static{position:static;display:inline-block}
.diag{align-self:start;display:flex;gap:8px;align-items:flex-start;font-size:12px;background:#EAF3DE;color:#27500A;border-radius:10px;padding:10px}
.diag.bad{background:#FCEBEB;color:#791F1F}
.event{display:flex;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--divider-color)}
.event:first-child{border-top:0}
.status{font-size:11px;padding:2px 9px;border-radius:10px;white-space:nowrap}
.calgrid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:3px}
.calh{font-size:10px;color:var(--secondary-text-color);text-align:center}
.cal{border-radius:6px;min-height:34px;padding:3px 4px;display:flex;flex-direction:column;justify-content:space-between;font-size:10px}
.cal b{font-weight:500;font-size:11px;text-align:right}
.cal.today{outline:2px solid var(--primary-text-color);outline-offset:-2px}
.calscale{flex:1;max-width:160px;height:8px;border-radius:4px;background:linear-gradient(90deg,rgba(99,153,34,.12),rgba(99,153,34,.92))}
.billrow{padding:6px 0;border-top:1px solid var(--divider-color)}
.billrow:first-child{border-top:0}
.subtabs{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.subtabs button:not(.round){font:inherit;font-size:13px;padding:5px 12px;border-radius:16px;border:1px solid var(--divider-color);background:var(--card-background-color);color:var(--secondary-text-color);cursor:pointer}
.subtabs button.on{background:#FAC775;border-color:#FAC775;color:#633806}
.sugg{display:flex;gap:9px;align-items:center;padding:6px 0;border-top:1px solid var(--divider-color)}
.sugg:first-child{border-top:0}
.rolehead{font-size:11px;font-weight:500;color:var(--secondary-text-color);text-transform:uppercase;letter-spacing:.04em;margin:10px 0 2px}
.rolehead:first-child{margin-top:0}
.qrow{display:grid;grid-template-columns:200px minmax(0,1fr) 110px;gap:10px;align-items:center;padding:5px 0;border-top:1px solid var(--divider-color)}
.qrow:first-child{border-top:0}
.qname code{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.qbar{display:grid;grid-template-columns:repeat(96,1fr);gap:1px;height:14px}
.qbar i{display:block;border-radius:1px}
.qval{text-align:right;font-size:12px}
.qrow.axis{border-top:0;padding-top:0}
.qaxis{display:flex;justify-content:space-between;font-size:10px;color:var(--secondary-text-color)}
.schema{width:100%;max-width:760px;display:block;margin:0 auto}
.schema .node{cursor:pointer}
.schema .node:hover rect{stroke-width:2.2}
.schema .node:focus{outline:none}
.nodedetail{margin-top:8px;padding:10px 12px;border-radius:10px;background:var(--secondary-background-color)}
a.copy{text-decoration:none}@media (max-width:600px){.round.refresh{display:none}.refresh-inline{display:flex}.grid3{grid-template-columns:repeat(2,minmax(0,1fr))}.battrow{grid-template-columns:minmax(0,1fr)}.qrow{grid-template-columns:minmax(0,1fr) 70px}.qrow .qbar{grid-column:1/-1;grid-row:2}.qrow.axis .qaxis{grid-column:1/-1}.cellrow{grid-template-columns:minmax(0,1fr)}
.kpis,.grid4{grid-template-columns:repeat(2,minmax(0,1fr))}.grid2,.ringrow{grid-template-columns:minmax(0,1fr)}.banner .title{font-size:15px}.banner.collapsed .tname{display:none}.banner:not(.collapsed) .titles{background:linear-gradient(90deg,var(--sky) 75%,transparent);padding-right:18px;position:relative;z-index:1}.barrow{grid-template-columns:80px minmax(0,1fr) 90px}}
`;

if (!customElements.get('energy-hub-panel')) {
  customElements.define('energy-hub-panel', EnergyHubPanel);
  console.info(`%c ENERGY-HUB %c v${ENERGY_HUB_PANEL_VERSION} `, 'color:#fff;background:#BA7517;font-weight:700', 'color:#BA7517;background:#fff');
}
