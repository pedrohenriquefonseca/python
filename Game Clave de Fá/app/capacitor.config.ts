import type { CapacitorConfig } from "@capacitor/cli"

// App nativo (iOS/Android) empacotado com Capacitor a partir do build Vite (dist).
// O projeto nativo (ios/, android/) é gerado por máquina com `npx cap add ios` e
// NÃO é versionado — a fonte da verdade é este config + o build web. Ver README.
const config: CapacitorConfig = {
  appId: "com.clavedefa.app", // troque pelo seu bundle id antes de publicar
  appName: "Clave de Fá",
  webDir: "dist",
  // Trava paisagem também é reforçada em runtime via @capacitor/screen-orientation
  // (ver main.ts), para sobreviver à regeneração do projeto nativo.
  ios: {
    contentInset: "never",
  },
  backgroundColor: "#000000", // letterbox preto fora da "tela" do jogo
}

export default config
