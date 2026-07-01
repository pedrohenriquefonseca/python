// Paleta "Neon Pink" (dark): pauta branca para leitura, fundo escuro e
// acentos magenta/ciano com cara de videogame. Escolhida em jun/2026.
export const theme = {
  bg: "#0A0612", // fundo da tela (escuro)
  band: "#14091F", // faixa de cabeçalho do HUD
  panel: "#FFFFFF", // pauta — fundo branco (leitura)
  ink: "#1A1A22", // notação sobre o branco (clave, linhas, notas)
  muted: "#8A6B9C", // texto auxiliar — legível no escuro e no branco
  accent: "#D11E6B", // linha de acerto + nota ativa (lê sobre o branco)
  altered: "#0C8577", // nota alterada pela armadura (teal escuro, lê sobre o branco)
  hud: "#FF2E88", // números do HUD (magenta vibrante, sobre o escuro)
  secondary: "#19E3D6", // ciano — destaques
  noteName: "#B81C5F", // nome da nota junto à linha de acerto
  posBand: "#FF2E88", // faixa "Posição de vara"
  posText: "#3D0822", // texto sobre a faixa magenta
  btn: "#242B3D", // botão de posição (cinza-azulado, separado do fundo)
  btnBorder: "#3E4A68", // borda do botão
  btnInk: "#19E3D6", // número do botão (ciano)
  btnActive: "#19E3D6", // botão pressionado / acerto
  btnActiveInk: "#0A0612", // número no botão ativo
} as const

export function applyThemeVars(el: HTMLElement = document.documentElement): void {
  for (const [key, value] of Object.entries(theme)) {
    el.style.setProperty(`--${key}`, value)
  }
}
