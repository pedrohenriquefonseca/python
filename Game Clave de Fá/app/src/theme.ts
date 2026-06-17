export const theme = {
  bg: "#F5F6FB",
  panel: "#FFFFFF",
  ink: "#222633",
  muted: "#8A8FA0",
  accent: "#5A5BE0",
  accent2: "#159E91",
  btn: "#EDEFF8",
  btnInk: "#222633",
} as const

export function applyThemeVars(el: HTMLElement = document.documentElement): void {
  for (const [key, value] of Object.entries(theme)) {
    el.style.setProperty(`--${key}`, value)
  }
}
