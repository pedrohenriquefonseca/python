interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  life: number
  maxLife: number
  r: number
  color: string
}

interface Ring {
  x: number
  y: number
  r: number
  maxR: number
  life: number
  color: string
}

// s = fator de tempo normalizado para ~60fps (dt / 16.667).
export class Particles {
  private parts: Particle[] = []
  private rings: Ring[] = []

  // Acerto: explosão celebrativa (mais partículas + anel) na cor do tier.
  explode(x: number, y: number, color: string, intensity: number): void {
    const n = Math.min(46, 14 + intensity)
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2
      const speed = 1.5 + Math.random() * 5
      this.parts.push({
        x, y,
        vx: Math.cos(a) * speed,
        vy: Math.sin(a) * speed,
        life: 28 + Math.random() * 18,
        maxLife: 46,
        r: 2 + Math.random() * 2.5,
        color,
      })
    }
    this.rings.push({ x, y, r: 6, maxR: 30 + Math.min(intensity, 28), life: 1, color })
  }

  // Erro/passagem: puff discreto, sem anel (erro gentil).
  puff(x: number, y: number, color: string): void {
    for (let i = 0; i < 8; i++) {
      const a = Math.random() * Math.PI * 2
      const speed = 1 + Math.random() * 2.4
      this.parts.push({
        x, y,
        vx: Math.cos(a) * speed,
        vy: Math.sin(a) * speed,
        life: 14 + Math.random() * 10,
        maxLife: 24,
        r: 1.5 + Math.random() * 1.5,
        color,
      })
    }
  }

  update(s: number): void {
    for (const p of this.parts) {
      p.x += p.vx * s
      p.y += p.vy * s
      p.vy += 0.12 * s
      p.vx *= Math.pow(0.99, s)
      p.life -= s
    }
    this.parts = this.parts.filter((p) => p.life > 0)
    for (const r of this.rings) {
      r.r += (r.maxR - r.r) * Math.min(1, 0.25 * s)
      r.life -= 0.06 * s
    }
    this.rings = this.rings.filter((r) => r.life > 0)
  }

  draw(ctx: CanvasRenderingContext2D): void {
    for (const r of this.rings) {
      ctx.globalAlpha = Math.max(0, r.life)
      ctx.strokeStyle = r.color
      ctx.lineWidth = 2.5
      ctx.beginPath()
      ctx.arc(r.x, r.y, r.r, 0, Math.PI * 2)
      ctx.stroke()
    }
    for (const p of this.parts) {
      const k = p.life / p.maxLife
      ctx.globalAlpha = Math.max(0, k)
      ctx.fillStyle = p.color
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r * k, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.globalAlpha = 1
  }
}
