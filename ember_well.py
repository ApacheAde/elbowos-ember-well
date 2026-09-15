#!/usr/bin/env python3
"""Ember Well — neon magnet-well arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/EMBER_WELL_ElbowOS.mp4")
TITLE, HANDLE = "EMBER WELL", "x.com/ElbowOS"

BG = (12, 8, 10)
CHAR = (28, 14, 16)
GOLD = (255, 186, 54)
AMBER = (255, 120, 32)
TEAL = (40, 230, 210)
ROSE = (255, 70, 110)
WHITE = (255, 246, 236)
VIO = (190, 90, 255)
ASH = (90, 78, 88)


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.display.quit()
            pygame.display.init()
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        self.font_lg = pygame.font.SysFont("DejaVu Sans", 56, bold=True)
        self.font = pygame.font.SysFont("DejaVu Sans", 36, bold=True)
        self.font_sm = pygame.font.SysFont("DejaVu Sans", 26)
        self.clock = pygame.time.Clock()
        self.x = W * 0.5
        self.y = 1580
        self.vx = 0
        self.pull = False
        self.score = self.combo = self.t = self.flash = 0
        self.lives = 3
        self.orbs, self.sparks, self.trail = [], [], []
        self.stars = [[random.randint(0, W), random.randint(0, H),
                       random.uniform(0.6, 2.4), random.choice((GOLD, AMBER, TEAL, ROSE))]
                      for _ in range(80)]
        self.ripples = []
        self.spawn_cd = 0
        self.reset()

    def reset(self):
        self.orbs.clear()
        self.lives = 3
        self.combo = 0
        self.x = W * 0.5
        self.spawn_cd = 4

    def burst(self, x, y, col, n=16):
        for _ in range(n):
            a = random.uniform(0, 6.2832)
            sp = random.uniform(3, 14)
            self.sparks.append([x, y, math.cos(a) * sp, math.sin(a) * sp, 18, col])

    def spawn(self):
        kind = "ember" if random.random() < 0.72 else "ash"
        lane = random.choice([180, 320, 460, 600, 740, 880])
        lane += random.randint(-28, 28)
        vy = random.uniform(7.5, 13.5)
        r = 22 if kind == "ember" else 26
        col = random.choice((GOLD, AMBER, TEAL)) if kind == "ember" else ASH
        self.orbs.append({"x": lane, "y": -40, "vy": vy, "r": r, "k": kind, "c": col, "w": 0.0})

    def step(self, keys, auto=False):
        self.t += 1
        ax = 0
        if auto:
            target = self.x
            embers = [o for o in self.orbs if o["k"] == "ember" and o["y"] < self.y + 40]
            if embers:
                embers.sort(key=lambda o: (self.y - o["y"]) + abs(o["x"] - self.x) * 0.35)
                target = embers[0]["x"]
                self.pull = abs(target - self.x) < 90 and embers[0]["y"] > 980
            else:
                self.pull = False
            ax = 1.8 if target > self.x + 12 else -1.8 if target < self.x - 12 else 0
        else:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                ax = -1.8
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                ax = 1.8
            self.pull = keys[pygame.K_SPACE] or keys[pygame.K_UP]
        self.vx = self.vx * 0.82 + ax * 16
        self.x = max(110, min(W - 110, self.x + self.vx))
        self.trail.append([self.x, self.y, 14])
        if len(self.trail) > 18:
            self.trail.pop(0)
        self.spawn_cd -= 1
        if self.spawn_cd <= 0:
            self.spawn()
            self.spawn_cd = max(8, 18 - self.t // 90)
        pull_r = 260 if self.pull else 0
        keep = []
        for o in self.orbs:
            if self.pull and o["k"] == "ember":
                dx, dy = self.x - o["x"], self.y - 36 - o["y"]
                d = math.hypot(dx, dy) or 1
                if d < pull_r:
                    o["x"] += dx / d * 9
                    o["y"] += dy / d * 7
            o["w"] += 0.18
            o["x"] += math.sin(o["w"] + o["y"] * 0.01) * (1.4 if o["k"] == "ember" else 0.6)
            o["y"] += o["vy"]
            hx, hy = self.x, self.y - 28
            if math.hypot(o["x"] - hx, o["y"] - hy) < o["r"] + 38:
                if o["k"] == "ember":
                    self.combo += 1
                    self.score += 80 + self.combo * 12
                    self.burst(o["x"], o["y"], o["c"])
                    self.ripples.append([o["x"], o["y"], 8, o["c"]])
                    self.flash = 6
                else:
                    self.lives -= 1
                    self.combo = 0
                    self.burst(o["x"], o["y"], ROSE, 22)
                    self.flash = 10
                    if self.lives <= 0:
                        self.score = max(0, self.score - 120)
                        self.reset()
                continue
            if o["y"] > H + 50:
                if o["k"] == "ember":
                    self.combo = 0
                continue
            keep.append(o)
        self.orbs = keep
        for s in self.sparks:
            s[0] += s[2]
            s[1] += s[3]
            s[3] += 0.35
            s[4] -= 1
        self.sparks = [s for s in self.sparks if s[4] > 0]
        for r in self.ripples:
            r[2] += 7
        self.ripples = [r for r in self.ripples if r[2] < 160]
        if self.flash:
            self.flash -= 1

    def draw(self):
        s = self.screen
        s.fill(BG)
        for st in self.stars:
            st[1] += st[2]
            if st[1] > H:
                st[1] = 0
                st[0] = random.randint(0, W)
            pygame.draw.circle(s, st[3], (int(st[0]), int(st[1])), 2)
        for y in range(0, H, 28):
            pulse = 10 + int(6 * math.sin(self.t * 0.08 + y * 0.02))
            pygame.draw.rect(s, (40 + pulse, 16, 18), (0, y, 70, 28))
            pygame.draw.rect(s, (40 + pulse, 16, 18), (W - 70, y, 70, 28))
            pygame.draw.line(s, AMBER, (70, y), (70, y + 28), 3)
            pygame.draw.line(s, TEAL, (W - 70, y), (W - 70, y + 28), 3)
        pygame.draw.rect(s, (48, 16, 12), (0, 1720, W, 200))
        for i in range(14):
            wx = 80 + i * 70
            hgt = 40 + 22 * math.sin(self.t * 0.12 + i)
            pygame.draw.ellipse(s, AMBER, (wx, 1760 - hgt * 0.3, 48, 28 + hgt * 0.4))
            pygame.draw.ellipse(s, GOLD, (wx + 10, 1774 - hgt * 0.2, 26, 16 + hgt * 0.2))
        if self.pull:
            pygame.draw.circle(s, (40, 90, 80), (int(self.x), int(self.y - 28)), 250, 2)
            pygame.draw.circle(s, TEAL, (int(self.x), int(self.y - 28)), 180, 1)
        for r in self.ripples:
            pygame.draw.circle(s, r[3], (int(r[0]), int(r[1])), int(r[2]), 3)
        for tr in self.trail:
            pygame.draw.circle(s, (80, 30, 20), (int(tr[0]), int(tr[1])), int(tr[2]))
            tr[2] *= 0.92
        for o in self.orbs:
            pygame.draw.circle(s, o["c"], (int(o["x"]), int(o["y"])), o["r"])
            pygame.draw.circle(s, WHITE, (int(o["x"] - 6), int(o["y"] - 6)), max(3, o["r"] // 4))
            if o["k"] == "ash":
                pygame.draw.circle(s, ROSE, (int(o["x"]), int(o["y"])), o["r"], 3)
        for sp in self.sparks:
            pygame.draw.circle(s, sp[5], (int(sp[0]), int(sp[1])), max(1, sp[4] // 4))
        bx, by = int(self.x), int(self.y)
        pygame.draw.polygon(s, TEAL if self.pull else GOLD, [
            (bx - 58, by), (bx + 58, by), (bx + 42, by + 48), (bx - 42, by + 48)
        ])
        pygame.draw.rect(s, WHITE, (bx - 50, by - 10, 100, 14), border_radius=6)
        pygame.draw.circle(s, TEAL if self.pull else AMBER, (bx, by - 28), 22)
        pygame.draw.circle(s, WHITE, (bx - 6, by - 34), 6)
        if self.flash:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 180, 80, 40))
            s.blit(veil, (0, 0))
        s.blit(self.font_lg.render(TITLE, True, GOLD), (36, 36))
        s.blit(self.font.render(f"SCORE  {self.score}", True, WHITE), (36, 108))
        s.blit(self.font.render(f"COMBO  x{self.combo}", True, TEAL), (36, 156))
        s.blit(self.font_sm.render(HANDLE, True, ROSE), (36, 210))
        for i in range(self.lives):
            pygame.draw.circle(s, AMBER, (W - 80 - i * 46, 70), 16)
        s.blit(self.font_sm.render("A/D move   SPACE pull", True, (180, 160, 150)), (36, H - 56))


def record(g):
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
        "-movflags", "+faststart", "-an", OUT,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    frames = FPS * SECS
    try:
        for _ in range(frames):
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    break
            g.step(None, auto=True)
            g.draw()
            frame = pygame.image.tostring(g.screen, "RGB")
            proc.stdin.write(frame)
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "ignore")[-800:]
        rc = proc.wait(timeout=60)
        if rc != 0:
            raise RuntimeError(f"ffmpeg failed rc={rc}\n{err}")
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        raise


def play(g):
    run = True
    while run:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                run = False
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                run = False
        g.step(pygame.key.get_pressed(), auto=False)
        g.draw()
        pygame.display.flip()
        g.clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    game = Game()
    if PLAY and not RECORD:
        play(game)
    else:
        record(game)
        print("wrote", OUT)
