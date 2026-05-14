#!/usr/bin/env python3
"""
命石象棋 - Pygame 主程序（含动画 + HiDPI + 命石详情）
"""
import sys
import os
import math
import time
import random
import threading
import pygame
from engine import *
from ai import ChessAI

# ============================================================
# HiDPI 环境变量 — 必须在 pygame.init() 之前设置
# ============================================================
os.environ['SDL_VIDEO_ALLOW_HIGHDPI'] = '1'  # macOS Retina 支持

# ============================================================
# 常量 — 逻辑坐标（窗口请求尺寸）
# ============================================================
CELL = 66
MARGIN_X = 50
MARGIN_Y = 50
PIECE_R = 28
BOARD_COLS = 9
BOARD_ROWS = 10
BOARD_W = CELL * 8 + MARGIN_X * 2
BOARD_H = CELL * 9 + MARGIN_Y * 2
PANEL_W = 300
WIN_W = BOARD_W + PANEL_W
WIN_H = BOARD_H + 80
FPS = 60

def _detect_hidpi_scale():
    """检测 macOS Retina 的实际 DPI 缩放比"""
    try:
        # 先创建临时窗口来检测真实物理/逻辑比
        tmp = pygame.display.set_mode((64, 64), pygame.HIDDEN if hasattr(pygame, 'HIDDEN') else 0)
        # Pygame 2.x 在 macOS Retina 下：
        # pygame.display.get_window_size() → 逻辑尺寸
        # screen.get_size() → 也是逻辑尺寸
        # 但实际 framebuffer 可能是 2x
        # 唯一可靠的检测方式是对比
        if hasattr(pygame.display, 'get_window_size'):
            win_w, _ = pygame.display.get_window_size()
            surf_w = tmp.get_width()
            if surf_w > 0 and win_w > 0:
                ratio = surf_w / win_w
                if ratio > 1.2:
                    return int(round(ratio))
        return 1
    except Exception:
        return 1

# 颜色
C_BG = (26, 26, 46)
C_BOARD = (200, 168, 110)
C_LINE = (58, 42, 16)
C_RED_PIECE = (204, 0, 0)
C_BLACK_PIECE = (34, 34, 34)
C_RED_BG = (255, 245, 230)
C_BLACK_BG = (240, 234, 208)
C_GOLD = (240, 192, 96)
C_HIGHLIGHT = (60, 200, 60, 80)
C_CAPTURE_HL = (255, 60, 60, 90)
C_SELECT = (240, 192, 96)
C_PANEL_BG = (22, 33, 62)
C_PANEL_BORDER = (40, 60, 100)
C_TEXT = (224, 224, 224)
C_TEXT_DIM = (150, 150, 150)
C_LUEXI_HL = (60, 180, 255, 80)
C_STUN = (100, 100, 255, 100)
C_FUBING = (0, 204, 255)
C_TOOLTIP_BG = (30, 30, 50, 240)
C_TOOLTIP_BORDER = (100, 130, 200)
C_RUNE_GLOW = (255, 200, 80, 60)

# ============================================================
# 动画系统
# ============================================================
class Animation:
    def __init__(self):
        self.active = False
        self.piece = None
        self.from_x = 0
        self.from_y = 0
        self.to_x = 0
        self.to_y = 0
        self.current_x = 0
        self.current_y = 0
        self.progress = 0.0
        self.duration = 0.25
        self.start_time = 0
        self.callback = None
        self.flash_pieces = []
        self.flash_start = 0
        self.flash_duration = 0.3
        self.particles = []

    def start_move(self, piece, fx, fy, tx, ty, callback=None):
        self.active = True
        self.piece = piece
        self.from_x = fx
        self.from_y = fy
        self.to_x = tx
        self.to_y = ty
        self.current_x = fx
        self.current_y = fy
        self.progress = 0.0
        self.start_time = time.time()
        self.callback = callback

    def start_flash(self, pieces):
        self.flash_pieces = pieces
        self.flash_start = time.time()

    def add_particles(self, x, y, color, count=12):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(40, 120)
            self.particles.append({
                'x': x, 'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': random.uniform(0.3, 0.8),
                'born': time.time(),
                'color': color,
                'size': random.uniform(2, 5),
            })

    def update(self, dt):
        if self.active:
            elapsed = time.time() - self.start_time
            self.progress = min(1.0, elapsed / self.duration)
            t = 1.0 - (1.0 - self.progress) ** 3
            self.current_x = self.from_x + (self.to_x - self.from_x) * t
            self.current_y = self.from_y + (self.to_y - self.from_y) * t
            if self.progress >= 1.0:
                self.active = False
                if self.callback:
                    self.callback()
                    self.callback = None

        now = time.time()
        alive = []
        for p in self.particles:
            age = now - p['born']
            if age < p['life']:
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['vy'] += 200 * dt
                alive.append(p)
        self.particles = alive

    def is_flashing(self):
        if not self.flash_pieces:
            return False
        return time.time() - self.flash_start < self.flash_duration

    def get_flash_alpha(self):
        elapsed = time.time() - self.flash_start
        if elapsed >= self.flash_duration:
            return 0
        t = elapsed / self.flash_duration
        return int(255 * (1.0 - t) * abs(math.sin(t * math.pi * 3)))


# ============================================================
# 字体管理
# ============================================================
class FontManager:
    def __init__(self, scale=1):
        pygame.font.init()
        self._cache = {}
        self.scale = scale
        self.chinese_font_path = self._find_chinese_font()

    def _find_chinese_font(self):
        candidates = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/Library/Fonts/Arial Unicode.ttf',
            '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def get(self, size, bold=False):
        """size 为逻辑大小，内部自动乘以 scale"""
        real_size = size * self.scale
        key = (real_size, bold)
        if key not in self._cache:
            if self.chinese_font_path:
                try:
                    f = pygame.font.Font(self.chinese_font_path, real_size)
                    f.set_bold(bold)
                    self._cache[key] = f
                    return f
                except Exception:
                    pass
            f = pygame.font.SysFont('pingfangsc,microsoftyahei,simhei,arial', real_size, bold=bold)
            self._cache[key] = f
        return self._cache[key]


# ============================================================
# 主游戏类
# ============================================================
class ChessGame:
    # 窗口缩放预设（相对于画布大小的比例）
    WINDOW_SCALES = [
        ('小', 0.50),
        ('中', 0.67),
        ('大', 0.85),
        ('全', 1.00),
    ]

    def __init__(self):
        pygame.init()

        # --------------------------------------------------
        # Retina / HiDPI 渲染策略：
        #
        #   离屏画布始终 2x（高分辨率绘制），然后 smoothscale 到窗口大小。
        #   用户可在设置页面选择窗口缩放比例。
        #   在 macOS Retina 上，窗口大小 = 画布原始大小时
        #   物理像素 1:1 映射（最清晰）；缩小后有轻微模糊但窗口更小。
        # --------------------------------------------------
        self.hidpi_scale = 2
        self.canvas_w = WIN_W * self.hidpi_scale
        self.canvas_h = WIN_H * self.hidpi_scale
        self.canvas = pygame.Surface((self.canvas_w, self.canvas_h))

        # 默认窗口缩放 = 67%（中）
        self.window_scale_idx = 1  # 对应 WINDOW_SCALES[1] = ('中', 0.67)
        self._apply_window_scale()

        pygame.display.set_caption('命石象棋')
        self.clock = pygame.time.Clock()

        self.fonts = FontManager(self.hidpi_scale)

        # 窗口尺寸设置按钮（在 setup 页面绘制）
        self._size_buttons = []

        self.game = GameState()
        self.game.init_board()
        self.phase = 'setup'

        self.game_mode = 'pve'
        self.ai_side = Side.BLACK
        self.player_side = Side.RED
        self.ai_difficulty = 'hard'
        self.ai_instance = None
        self.ai_thinking = False
        self.ai_thread = None
        self.ai_result = None

        self.selected_piece = None
        self.legal_moves = []
        self.highlight_cells = []
        self.hover_piece = None
        self.mouse_pos = (0, 0)  # 逻辑坐标

        self.anim = Animation()
        self.log_lines = []
        self.log_scroll = 0

        self.setup_scroll = 0
        self.rune_selections = {}
        self.setup_buttons = []
        self.mode_buttons = []

        # Tooltip 相关
        self.tooltip_piece = None
        self.tooltip_show_time = 0
        self.TOOLTIP_DELAY = 0.15  # 悬浮150ms后显示

        self.show_win_modal = False
        self.win_text = ''
        self.action_prompt = None

        # 面板tab: 'info' | 'runes'
        self.panel_tab = 'info'

        self._init_setup_ui()

    def _init_setup_ui(self):
        self.rune_selections.clear()
        target = [p for p in self.game.pieces if (self.game_mode == 'pvp' or p.side == self.player_side)]
        for p in target:
            self.rune_selections[p.id] = 0

    def _screen_to_logical(self, sx, sy):
        """将窗口坐标转换为画布坐标（窗口可能小于画布）"""
        ratio = self.canvas_w / self.win_w
        return int(sx * ratio), int(sy * ratio)

    def _apply_window_scale(self):
        """根据 window_scale_idx 设置窗口大小"""
        _, scale = self.WINDOW_SCALES[self.window_scale_idx]
        self.win_w = int(self.canvas_w * scale)
        self.win_h = int(self.canvas_h * scale)
        self.screen = pygame.display.set_mode((self.win_w, self.win_h))

    def set_window_scale(self, idx):
        """切换窗口尺寸"""
        if 0 <= idx < len(self.WINDOW_SCALES) and idx != self.window_scale_idx:
            self.window_scale_idx = idx
            self._apply_window_scale()
            pygame.display.set_caption('命石象棋')

    # ============================================================
    # 坐标转换 — 返回画布物理像素坐标
    # ============================================================
    @property
    def S(self):
        """快捷缩放因子"""
        return self.hidpi_scale

    def board_x(self, col):
        return (MARGIN_X + col * CELL) * self.S

    def board_y(self, row):
        return (MARGIN_Y + (9 - row) * CELL) * self.S

    def screen_to_board(self, mx, my):
        pr = (PIECE_R + 6) * self.S
        for c in range(9):
            for r in range(10):
                dx = mx - self.board_x(c)
                dy = my - self.board_y(r)
                if dx * dx + dy * dy < pr * pr:
                    return c, r
        return None, None

    # ============================================================
    # 绘制：棋盘
    # ============================================================
    def draw_board(self, surface):
        S = self.S
        board_rect = pygame.Rect(
            (MARGIN_X - 30) * S, (MARGIN_Y - 30) * S,
            (CELL * 8 + 60) * S, (CELL * 9 + 60) * S)
        pygame.draw.rect(surface, C_BOARD, board_rect)
        pygame.draw.rect(surface, (90, 70, 30), board_rect, max(1, 2 * S))

        for r in range(10):
            pygame.draw.line(surface, C_LINE,
                             (self.board_x(0), self.board_y(r)),
                             (self.board_x(8), self.board_y(r)), max(1, S))
        for c in range(9):
            pygame.draw.line(surface, C_LINE,
                             (self.board_x(c), self.board_y(0)),
                             (self.board_x(c), self.board_y(4)), max(1, S))
            pygame.draw.line(surface, C_LINE,
                             (self.board_x(c), self.board_y(5)),
                             (self.board_x(c), self.board_y(9)), max(1, S))
        pygame.draw.line(surface, C_LINE,
                         (self.board_x(0), self.board_y(0)),
                         (self.board_x(0), self.board_y(9)), max(1, S))
        pygame.draw.line(surface, C_LINE,
                         (self.board_x(8), self.board_y(0)),
                         (self.board_x(8), self.board_y(9)), max(1, S))

        # 九宫格斜线
        pygame.draw.line(surface, C_LINE,
                         (self.board_x(3), self.board_y(0)),
                         (self.board_x(5), self.board_y(2)), max(1, S))
        pygame.draw.line(surface, C_LINE,
                         (self.board_x(5), self.board_y(0)),
                         (self.board_x(3), self.board_y(2)), max(1, S))
        pygame.draw.line(surface, C_LINE,
                         (self.board_x(3), self.board_y(7)),
                         (self.board_x(5), self.board_y(9)), max(1, S))
        pygame.draw.line(surface, C_LINE,
                         (self.board_x(5), self.board_y(7)),
                         (self.board_x(3), self.board_y(9)), max(1, S))

        # 星位标记
        star_positions = [(1,2),(7,2),(1,7),(7,7),(0,3),(2,3),(4,3),(6,3),(8,3),
                          (0,6),(2,6),(4,6),(6,6),(8,6)]
        for sc, sr in star_positions:
            sx, sy = self.board_x(sc), self.board_y(sr)
            size = 4 * S
            offsets = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
            for ox, oy in offsets:
                skip = False
                if sc == 0 and ox == -1:
                    skip = True
                if sc == 8 and ox == 1:
                    skip = True
                if not skip:
                    bx = sx + ox * 5 * S
                    by = sy + oy * 5 * S
                    pygame.draw.line(surface, C_LINE, (bx, by), (bx + ox * size, by), max(1, S))
                    pygame.draw.line(surface, C_LINE, (bx, by), (bx, by + oy * size), max(1, S))

        # 楚河汉界
        font = self.fonts.get(20, bold=True)
        river_y = (self.board_y(4) + self.board_y(5)) // 2
        txt1 = font.render('楚  河', True, C_LINE)
        txt2 = font.render('漢  界', True, C_LINE)
        surface.blit(txt1, (self.board_x(1) - txt1.get_width() // 2 + 20 * S, river_y - txt1.get_height() // 2))
        surface.blit(txt2, (self.board_x(6) - txt2.get_width() // 2 + 10 * S, river_y - txt2.get_height() // 2))

    def draw_highlights(self, surface):
        S = self.S
        PR = PIECE_R * S
        for h in self.highlight_cells:
            x, y = self.board_x(h['col']), self.board_y(h['row'])
            is_cap = h.get('type') == 'capture'
            dim = PR * 2 + 8 * S
            s = pygame.Surface((dim, dim), pygame.SRCALPHA)
            color = (255, 60, 60, 90) if is_cap else (60, 200, 60, 70)
            pygame.draw.circle(s, color, (dim // 2, dim // 2), PR + 2 * S)
            surface.blit(s, (x - dim // 2, y - dim // 2))
            if is_cap:
                pygame.draw.circle(surface, (255, 68, 68), (x, y), PR + 4 * S, max(1, 2 * S))

        if self.selected_piece:
            sx = self.board_x(self.selected_piece.col)
            sy = self.board_y(self.selected_piece.row)
            pygame.draw.circle(surface, C_SELECT, (sx, sy), PR + 5 * S, max(1, 3 * S))

    def draw_piece(self, surface, p, x=None, y=None, alpha=255):
        S = self.S
        PR = PIECE_R * S
        if x is None:
            x = self.board_x(p.col)
        if y is None:
            y = self.board_y(p.row)

        # 命石光环
        if p.rune != Rune.NONE:
            glow_dim = PR * 2 + 16 * S
            glow_surf = pygame.Surface((glow_dim, glow_dim), pygame.SRCALPHA)
            pulse = math.sin(time.time() * 2.0) * 0.3 + 0.7
            glow_alpha = int(50 * pulse)
            pygame.draw.circle(glow_surf, (255, 200, 80, glow_alpha),
                             (glow_dim // 2, glow_dim // 2), PR + 6 * S)
            surface.blit(glow_surf, (x - glow_dim // 2, y - glow_dim // 2))

        # 阴影
        shadow_dim = PR * 2 + 6 * S
        shadow = pygame.Surface((shadow_dim, shadow_dim), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (0, 0, 0, 50), (shadow_dim // 2, shadow_dim // 2), PR + 1 * S)
        surface.blit(shadow, (x - shadow_dim // 2 + 2 * S, y - shadow_dim // 2 + 2 * S))

        # 棋子主体
        bg = C_RED_BG if p.side == Side.RED else C_BLACK_BG
        piece_dim = PR * 2
        piece_surf = pygame.Surface((piece_dim, piece_dim), pygame.SRCALPHA)
        pygame.draw.circle(piece_surf, (*bg, alpha), (PR, PR), PR)

        # 双层边框
        outer_color = (139, 0, 0, alpha) if p.side == Side.RED else (51, 51, 51, alpha)
        inner_color = (180, 50, 50, alpha) if p.side == Side.RED else (80, 80, 80, alpha)
        pygame.draw.circle(piece_surf, outer_color, (PR, PR), PR - 1 * S, max(1, 2 * S))
        pygame.draw.circle(piece_surf, inner_color, (PR, PR), PR - 4 * S, max(1, 1 * S))

        # 文字
        txt_color = (204, 0, 0) if p.side == Side.RED else (34, 34, 34)
        font = self.fonts.get(22, bold=True)
        txt = font.render(p.name, True, txt_color)
        piece_surf.blit(txt, (PR - txt.get_width() // 2, PR - txt.get_height() // 2 + 1 * S))

        # 命石角标
        if p.rune != Rune.NONE:
            badge_size = 8 * S
            badge_x = piece_dim - badge_size - 2 * S
            badge_y = 2 * S
            pygame.draw.circle(piece_surf, (255, 200, 80, alpha), (badge_x, badge_y + badge_size), badge_size)
            pygame.draw.circle(piece_surf, (180, 140, 40, alpha), (badge_x, badge_y + badge_size), badge_size, max(1, S))
            rune_char = RUNE_NAMES[p.rune][0]
            sfont = self.fonts.get(10, bold=True)
            st = sfont.render(rune_char, True, (60, 40, 10))
            piece_surf.blit(st, (badge_x - st.get_width() // 2, badge_y + badge_size - st.get_height() // 2))

        surface.blit(piece_surf, (x - PR, y - PR))

        # 眩晕标记
        if p.stun_next_turn:
            stun_surf = pygame.Surface((PR * 2, PR * 2), pygame.SRCALPHA)
            pygame.draw.circle(stun_surf, (100, 100, 255, 100), (PR, PR), PR)
            surface.blit(stun_surf, (x - PR, y - PR))
            sfont = self.fonts.get(12, bold=True)
            st = sfont.render('晕', True, (100, 100, 255))
            surface.blit(st, (x - st.get_width() // 2, y + PR - 14 * S))

        # 伏兵标记（前8回合内且未移动）
        if p.rune == Rune.BING_FUBING and not p.has_moved:
            if p.side == Side.RED:
                side_turns = (self.game.turn_number + 1) // 2
            else:
                side_turns = self.game.turn_number // 2
            if side_turns <= 8:
                pygame.draw.circle(surface, C_FUBING, (x, y), PR + 1 * S, max(1, 2 * S))

    def draw_pieces(self, surface):
        for p in self.game.alive_pieces():
            if self.anim.active and self.anim.piece and p.id == self.anim.piece.id:
                self.draw_piece(surface, p, int(self.anim.current_x), int(self.anim.current_y))
                continue
            if self.anim.is_flashing() and p in self.anim.flash_pieces:
                alpha = self.anim.get_flash_alpha()
                self.draw_piece(surface, p, alpha=alpha)
                continue
            self.draw_piece(surface, p)

    def draw_particles(self, surface):
        S = self.S
        now = time.time()
        for pt in self.anim.particles:
            age = now - pt['born']
            alpha = int(255 * (1.0 - age / pt['life']))
            alpha = max(0, min(255, alpha))
            sz = int(pt['size'] * 2 * S)
            if sz < 2:
                sz = 2
            s = pygame.Surface((sz, sz), pygame.SRCALPHA)
            pygame.draw.circle(s, (*pt['color'], alpha), (sz // 2, sz // 2), sz // 2)
            # 粒子位置已是物理像素坐标（从 board_x/board_y 获取）
            surface.blit(s, (int(pt['x'] - sz // 2), int(pt['y'] - sz // 2)))

    def draw_luexi_range(self, surface):
        if not self.game.pending_luexi_move:
            return
        S = self.S
        PR = PIECE_R * S
        che = self.game.pending_luexi_move['che']
        for dc, dr in [(0,1),(0,-1),(1,0),(-1,0)]:
            for i in range(1, 4):
                nc, nr = che.col + dc * i, che.row + dr * i
                if not self.game.is_in_board(nc, nr):
                    break
                if self.game.piece_at(nc, nr):
                    break
                x, y = self.board_x(nc), self.board_y(nr)
                dim = PR * 2 + 4 * S
                s = pygame.Surface((dim, dim), pygame.SRCALPHA)
                pygame.draw.circle(s, (60, 180, 255, 80), (dim // 2, dim // 2), PR + 2 * S)
                surface.blit(s, (x - dim // 2, y - dim // 2))

    # ============================================================
    # Tooltip：棋子悬浮详情
    # ============================================================
    def draw_tooltip(self, surface):
        """在棋子上悬浮时显示命石详情"""
        if self.phase != 'playing':
            return
        if not self.hover_piece:
            return
        if self.selected_piece:
            return
        if self.tooltip_piece != self.hover_piece:
            return
        if time.time() - self.tooltip_show_time < self.TOOLTIP_DELAY:
            return

        S = self.S
        p = self.hover_piece
        mx, my = self.mouse_pos

        lines = []
        side_str = '红方' if p.side == Side.RED else '黑方'
        lines.append(('title', f"{side_str} {p.name}"))

        if p.rune != Rune.NONE:
            can_see = (p.side == self.player_side) or self.game_mode == 'pvp'
            if can_see:
                lines.append(('rune_name', RUNE_NAMES[p.rune]))
                lines.append(('desc', RUNE_DESCS[p.rune]))
            else:
                lines.append(('rune_name', '命石：???'))
                lines.append(('desc', '对方命石效果未知'))
        else:
            lines.append(('desc', '未装备命石'))

        if p.stun_next_turn:
            lines.append(('status', '状态：眩晕（下回合不能行动）'))
        if p.rune == Rune.BING_FUBING and not p.has_moved:
            if p.side == Side.RED:
                side_turns = (self.game.turn_number + 1) // 2
            else:
                side_turns = self.game.turn_number // 2
            if side_turns <= 8:
                remain = 8 - side_turns
                lines.append(('status', f'状态：伏兵激活中（剩余{remain}回合，被吃则同归于尽）'))
            else:
                lines.append(('status', '状态：伏兵已失效（超过8回合）'))

        font_title = self.fonts.get(14, bold=True)
        font_rune = self.fonts.get(13, bold=True)
        font_desc = self.fonts.get(11)
        font_status = self.fonts.get(11, bold=True)

        padding = 10 * S
        line_gap = 4 * S
        max_w = 220 * S
        rendered = []

        for ltype, text in lines:
            if ltype == 'title':
                f = font_title
                c = C_TEXT
            elif ltype == 'rune_name':
                f = font_rune
                c = C_GOLD
            elif ltype == 'status':
                f = font_status
                c = (120, 180, 255)
            else:
                f = font_desc
                c = C_TEXT_DIM

            wrapped = self._wrap_text(text, f, max_w - padding * 2)
            for wl in wrapped:
                surf = f.render(wl, True, c)
                rendered.append(surf)

        total_h = sum(s.get_height() + line_gap for s in rendered) + padding * 2 - line_gap
        total_w = max(s.get_width() for s in rendered) + padding * 2
        total_w = max(total_w, 140 * S)

        tx = mx + 16 * S
        ty = my - total_h - 8 * S
        if tx + total_w > BOARD_W * S:
            tx = mx - total_w - 16 * S
        if ty < 4 * S:
            ty = my + 20 * S
        if tx < 4 * S:
            tx = 4 * S

        tip_surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
        pygame.draw.rect(tip_surf, C_TOOLTIP_BG, (0, 0, total_w, total_h), border_radius=6 * S)
        pygame.draw.rect(tip_surf, C_TOOLTIP_BORDER, (0, 0, total_w, total_h), max(1, S), border_radius=6 * S)

        cy = padding
        for s in rendered:
            tip_surf.blit(s, (padding, cy))
            cy += s.get_height() + line_gap

        surface.blit(tip_surf, (tx, ty))

    # ============================================================
    # 绘制：右侧面板
    # ============================================================
    def draw_panel(self, surface):
        S = self.S
        panel_x = BOARD_W * S
        panel_rect = pygame.Rect(panel_x, 0, PANEL_W * S, WIN_H * S)
        pygame.draw.rect(surface, C_PANEL_BG, panel_rect)
        pygame.draw.line(surface, C_PANEL_BORDER, (panel_x, 0), (panel_x, WIN_H * S), max(1, 2 * S))

        y = 10 * S
        font_title = self.fonts.get(15, bold=True)
        font_normal = self.fonts.get(12)
        font_small = self.fonts.get(11)
        font_tab = self.fonts.get(12, bold=True)

        side = self.game.current_side
        side_name = '红方' if side == Side.RED else '黑方'
        is_ai = self.game_mode == 'pve' and side == self.ai_side
        color = (255, 68, 68) if side == Side.RED else (200, 200, 200)
        ai_tag = ' [AI]' if is_ai else ''
        turn_txt = f"{side_name}{ai_tag} 走棋"
        t = font_title.render(turn_txt, True, color)
        surface.blit(t, (panel_x + 12 * S, y))
        y += 22 * S

        round_num = self.game.turn_number // 2 + 1
        t = font_small.render(f"第 {round_num} 回合", True, C_TEXT_DIM)
        surface.blit(t, (panel_x + 12 * S, y))
        y += 20 * S

        if self.ai_thinking:
            dots = '.' * (int(time.time() * 3) % 4)
            t = font_normal.render(f"AI 思考中{dots}", True, (102, 204, 102))
            surface.blit(t, (panel_x + 12 * S, y))
            y += 18 * S

        y += 4 * S
        pygame.draw.line(surface, C_PANEL_BORDER, (panel_x + 8 * S, y), (panel_x + PANEL_W * S - 8 * S, y))
        y += 6 * S

        tab_info_rect = pygame.Rect(panel_x + 10 * S, y, 80 * S, 24 * S)
        tab_rune_rect = pygame.Rect(panel_x + 96 * S, y, 80 * S, 24 * S)

        for tab_rect, tab_val, tab_label in [
            (tab_info_rect, 'info', '行动记录'),
            (tab_rune_rect, 'runes', '命石总览'),
        ]:
            active = self.panel_tab == tab_val
            bg_c = (60, 80, 120) if active else (35, 45, 70)
            pygame.draw.rect(surface, bg_c, tab_rect, border_radius=4 * S)
            if active:
                pygame.draw.rect(surface, C_GOLD, tab_rect, max(1, S), border_radius=4 * S)
            tc = C_GOLD if active else C_TEXT_DIM
            t = font_tab.render(tab_label, True, tc)
            surface.blit(t, (tab_rect.centerx - t.get_width() // 2, tab_rect.centery - t.get_height() // 2))

        self._tab_info_rect = tab_info_rect
        self._tab_rune_rect = tab_rune_rect
        y += 30 * S

        if self.panel_tab == 'info':
            self._draw_panel_info(surface, panel_x, y, font_title, font_normal, font_small)
        else:
            self._draw_panel_runes(surface, panel_x, y, font_title, font_normal, font_small)

        # 窗口大小选择（重新开始按钮上方）
        size_y = WIN_H * S - 72 * S
        font_sz = self.fonts.get(10)
        t_label = font_sz.render('窗口:', True, C_TEXT_DIM)
        sx = panel_x + 12 * S
        surface.blit(t_label, (sx, size_y + 4 * S))
        sx += t_label.get_width() + 4 * S
        self._size_buttons = []
        for i, (label, _) in enumerate(self.WINDOW_SCALES):
            rect = pygame.Rect(sx, size_y, 48 * S, 22 * S)
            active = i == self.window_scale_idx
            color = C_GOLD if active else (50, 50, 70)
            pygame.draw.rect(surface, color, rect, border_radius=4 * S)
            tc = C_BG if active else C_TEXT_DIM
            t = font_sz.render(label, True, tc)
            surface.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))
            self._size_buttons.append((rect, i))
            sx += 54 * S

        btn_y = WIN_H * S - 38 * S
        btn_rect = pygame.Rect(panel_x + 12 * S, btn_y, PANEL_W * S - 24 * S, 28 * S)
        pygame.draw.rect(surface, (68, 68, 68), btn_rect, border_radius=6 * S)
        t = font_normal.render("重新开始", True, C_TEXT)
        surface.blit(t, (btn_rect.centerx - t.get_width() // 2, btn_rect.centery - t.get_height() // 2))
        self._restart_btn_rect = btn_rect

    def _draw_panel_info(self, surface, panel_x, y, font_title, font_normal, font_small):
        """绘制行动记录面板"""
        S = self.S
        target_piece = self.selected_piece or self.hover_piece
        if target_piece:
            p = target_piece
            tc = (255, 68, 68) if p.side == Side.RED else (200, 200, 200)
            t = font_title.render(p.name, True, tc)
            surface.blit(t, (panel_x + 12 * S, y))
            y += 20 * S
            if p.rune != Rune.NONE:
                can_see = (p.side == self.player_side) or self.game_mode == 'pvp'
                if can_see:
                    t = font_normal.render(RUNE_NAMES[p.rune], True, C_GOLD)
                    surface.blit(t, (panel_x + 12 * S, y))
                    y += 16 * S
                    desc = RUNE_DESCS[p.rune]
                    for line in self._wrap_text(desc, font_small, PANEL_W * S - 28 * S):
                        t = font_small.render(line, True, C_TEXT_DIM)
                        surface.blit(t, (panel_x + 12 * S, y))
                        y += 14 * S
                else:
                    t = font_small.render("命石: ???", True, C_TEXT_DIM)
                    surface.blit(t, (panel_x + 12 * S, y))
                    y += 14 * S
            else:
                t = font_small.render("未装备命石", True, C_TEXT_DIM)
                surface.blit(t, (panel_x + 12 * S, y))
                y += 14 * S
            y += 4 * S
            pygame.draw.line(surface, C_PANEL_BORDER, (panel_x + 8 * S, y), (panel_x + PANEL_W * S - 8 * S, y))
            y += 6 * S

        t = font_title.render("行动记录", True, C_GOLD)
        surface.blit(t, (panel_x + 12 * S, y))
        y += 20 * S

        max_lines = (WIN_H * S - y - 50 * S) // (14 * S)
        visible = self.log_lines[-max_lines:] if len(self.log_lines) > max_lines else self.log_lines
        for line in visible:
            lc = (255, 107, 107) if '吃' in line else C_TEXT_DIM
            t = font_small.render(line, True, lc)
            if t.get_width() > PANEL_W * S - 28 * S:
                t = font_small.render(line[:28] + '...', True, lc)
            surface.blit(t, (panel_x + 12 * S, y))
            y += 14 * S

    def _draw_panel_runes(self, surface, panel_x, y, font_title, font_normal, font_small):
        """绘制命石总览面板"""
        S = self.S
        for side, side_name in [(Side.RED, '红方'), (Side.BLACK, '黑方')]:
            tc = (255, 68, 68) if side == Side.RED else (200, 200, 200)
            t = font_title.render(side_name, True, tc)
            surface.blit(t, (panel_x + 12 * S, y))
            y += 20 * S

            pieces = [p for p in self.game.alive_pieces() if p.side == side]
            for p in pieces:
                can_see = (side == self.player_side) or self.game_mode == 'pvp'

                name_t = font_small.render(p.name, True, tc)
                surface.blit(name_t, (panel_x + 16 * S, y))

                if p.rune != Rune.NONE:
                    if can_see:
                        rune_t = font_small.render(RUNE_NAMES[p.rune], True, C_GOLD)
                    else:
                        rune_t = font_small.render('???', True, C_TEXT_DIM)
                else:
                    rune_t = font_small.render('-', True, (80, 80, 80))

                surface.blit(rune_t, (panel_x + 56 * S, y))
                y += 15 * S

                if y > WIN_H * S - 60 * S:
                    t = font_small.render('...', True, C_TEXT_DIM)
                    surface.blit(t, (panel_x + 16 * S, y))
                    return

            y += 6 * S
            pygame.draw.line(surface, C_PANEL_BORDER, (panel_x + 8 * S, y), (panel_x + PANEL_W * S - 8 * S, y))
            y += 6 * S

    def _wrap_text(self, text, font, max_width):
        lines = []
        current = ''
        for ch in text:
            test = current + ch
            if font.size(test)[0] > max_width:
                lines.append(current)
                current = ch
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    # ============================================================
    # 绘制：配置界面
    # ============================================================
    def draw_setup(self, surface):
        S = self.S
        surface.fill(C_BG)
        font_title = self.fonts.get(26, bold=True)
        font_sub = self.fonts.get(13)
        font_normal = self.fonts.get(12)
        font_small = self.fonts.get(11)
        font_btn = self.fonts.get(14, bold=True)

        y = 12 * S
        t = font_title.render('命石象棋', True, C_GOLD)
        surface.blit(t, (WIN_W * S // 2 - t.get_width() // 2, y))
        y += 34 * S

        t = font_sub.render('为你的棋子选择命石，制定独特的战术策略', True, C_TEXT_DIM)
        surface.blit(t, (WIN_W * S // 2 - t.get_width() // 2, y))
        y += 26 * S

        modes = [('pvp', '双人对弈'), ('pve', '人机对弈')]
        self.mode_buttons = []
        mx = WIN_W * S // 2 - 160 * S
        for val, label in modes:
            rect = pygame.Rect(mx, y, 140 * S, 30 * S)
            active = self.game_mode == val
            color = C_GOLD if active else (60, 60, 80)
            pygame.draw.rect(surface, color, rect, border_radius=6 * S)
            tc = C_BG if active else C_TEXT
            t = font_normal.render(label, True, tc)
            surface.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))
            self.mode_buttons.append((rect, val))
            mx += 160 * S

        y += 40 * S

        if self.game_mode == 'pve':
            diffs = [('easy', '简单'), ('normal', '中等'), ('hard', '困难')]
            self._diff_buttons = []
            dx = WIN_W * S // 2 - 220 * S
            for val, label in diffs:
                rect = pygame.Rect(dx, y, 90 * S, 26 * S)
                active = self.ai_difficulty == val
                color = C_GOLD if active else (50, 50, 80)
                pygame.draw.rect(surface, color, rect, border_radius=5 * S)
                tc = C_BG if active else C_TEXT
                t = font_small.render(label, True, tc)
                surface.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))
                self._diff_buttons.append((rect, val))
                dx += 104 * S

            sides_opt = [('black', 'AI执黑'), ('red', 'AI执红')]
            self._side_buttons = []
            for val, label in sides_opt:
                rect = pygame.Rect(dx, y, 86 * S, 26 * S)
                active = (self.ai_side == Side.RED and val == 'red') or (self.ai_side == Side.BLACK and val == 'black')
                color = C_GOLD if active else (50, 50, 80)
                pygame.draw.rect(surface, color, rect, border_radius=5 * S)
                tc = C_BG if active else C_TEXT
                t = font_small.render(label, True, tc)
                surface.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))
                self._side_buttons.append((rect, val))
                dx += 100 * S
            y += 36 * S
        else:
            self._diff_buttons = []
            self._side_buttons = []

        t = font_title.render('命石配置', True, C_GOLD)
        surface.blit(t, (24 * S, y))
        y += 32 * S

        sides = [self.player_side] if self.game_mode == 'pve' else [Side.RED, Side.BLACK]
        self.setup_buttons = []
        card_w = 190 * S
        card_h = 56 * S
        gap = 6 * S
        cols = max(1, (WIN_W * S - 50 * S) // (card_w + gap))

        for side in sides:
            if self.game_mode == 'pvp':
                side_label = '红方' if side == Side.RED else '黑方'
            else:
                side_label = '红方（你）' if side == Side.RED else '黑方（你）'
            tc = (255, 68, 68) if side == Side.RED else (200, 200, 200)
            t = font_normal.render(side_label, True, tc)
            surface.blit(t, (24 * S, y))
            y += 20 * S

            pieces = [p for p in self.game.pieces if p.side == side]
            order = [PieceType.JIANG, PieceType.SHI, PieceType.XIANG, PieceType.MA,
                     PieceType.CHE, PieceType.PAO, PieceType.BING]
            ordered = []
            for pt in order:
                ordered.extend([pp for pp in pieces if pp.type == pt])

            col_idx = 0
            for p in ordered:
                cx = 24 * S + col_idx * (card_w + gap)
                cy = y

                card_rect = pygame.Rect(cx, cy, card_w, card_h)
                pygame.draw.rect(surface, (26, 26, 62), card_rect, border_radius=6 * S)
                pygame.draw.rect(surface, (51, 51, 51), card_rect, max(1, S), border_radius=6 * S)

                tc = (255, 68, 68) if p.side == Side.RED else (200, 200, 200)
                t = font_normal.render(p.name, True, tc)
                surface.blit(t, (cx + 8 * S, cy + 5 * S))

                opts = RUNE_OPTIONS.get(p.type, [Rune.NONE])
                idx = self.rune_selections.get(p.id, 0)
                if idx >= len(opts):
                    idx = 0
                current_rune = opts[idx]

                arrow_l = pygame.Rect(cx + 6 * S, cy + 28 * S, 22 * S, 22 * S)
                arrow_r = pygame.Rect(cx + card_w - 28 * S, cy + 28 * S, 22 * S, 22 * S)

                pygame.draw.rect(surface, (50, 50, 80), arrow_l, border_radius=3 * S)
                pygame.draw.rect(surface, (50, 50, 80), arrow_r, border_radius=3 * S)
                t = font_small.render('<', True, C_TEXT)
                surface.blit(t, (arrow_l.centerx - t.get_width() // 2, arrow_l.centery - t.get_height() // 2))
                t = font_small.render('>', True, C_TEXT)
                surface.blit(t, (arrow_r.centerx - t.get_width() // 2, arrow_r.centery - t.get_height() // 2))

                rname = RUNE_NAMES[current_rune]
                rc = C_GOLD if current_rune != Rune.NONE else C_TEXT_DIM
                t = font_small.render(rname, True, rc)
                mid_x = (arrow_l.right + arrow_r.left) // 2
                surface.blit(t, (mid_x - t.get_width() // 2, cy + 28 * S + 11 * S - t.get_height() // 2))

                self.setup_buttons.append(('rune_left', arrow_l, p.id))
                self.setup_buttons.append(('rune_right', arrow_r, p.id))

                col_idx += 1
                if col_idx >= cols:
                    col_idx = 0
                    y += card_h + gap
            if col_idx > 0:
                y += card_h + gap
            y += 8 * S

        if self.game_mode == 'pve':
            ai_side_name = '红方' if self.ai_side == Side.RED else '黑方'
            t = font_small.render(f"{ai_side_name} AI 将自动选择命石配置", True, C_TEXT_DIM)
            surface.blit(t, (WIN_W * S // 2 - t.get_width() // 2, y))
            y += 22 * S

        y += 8 * S
        btn_w = 130 * S
        btn_gap = 16 * S
        total_w = btn_w * 2 + btn_gap
        bx = WIN_W * S // 2 - total_w // 2

        rand_rect = pygame.Rect(bx, y, btn_w, 34 * S)
        pygame.draw.rect(surface, (68, 68, 68), rand_rect, border_radius=8 * S)
        t = font_btn.render('随机', True, C_TEXT)
        surface.blit(t, (rand_rect.centerx - t.get_width() // 2, rand_rect.centery - t.get_height() // 2))
        self.setup_buttons.append(('random', rand_rect, None))

        start_rect = pygame.Rect(bx + btn_w + btn_gap, y, btn_w, 34 * S)
        pygame.draw.rect(surface, C_GOLD, start_rect, border_radius=8 * S)
        t = font_btn.render('开始对弈', True, C_BG)
        surface.blit(t, (start_rect.centerx - t.get_width() // 2, start_rect.centery - t.get_height() // 2))
        self.setup_buttons.append(('start', start_rect, None))

        # 窗口尺寸选择（底部）
        y += 50 * S
        font_sz = self.fonts.get(11)
        t = font_sz.render('窗口大小：', True, C_TEXT_DIM)
        sx = WIN_W * S // 2 - 180 * S
        surface.blit(t, (sx, y + 4 * S))
        sx += t.get_width() + 8 * S
        self._size_buttons = []
        for i, (label, _) in enumerate(self.WINDOW_SCALES):
            rect = pygame.Rect(sx, y, 56 * S, 26 * S)
            active = i == self.window_scale_idx
            color = C_GOLD if active else (55, 55, 75)
            pygame.draw.rect(surface, color, rect, border_radius=5 * S)
            tc = C_BG if active else C_TEXT
            t = font_sz.render(label, True, tc)
            surface.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))
            self._size_buttons.append((rect, i))
            sx += 64 * S

    # ============================================================
    # 绘制：胜利弹窗
    # ============================================================
    def draw_win_modal(self, surface):
        if not self.show_win_modal:
            return
        S = self.S
        overlay = pygame.Surface((WIN_W * S, WIN_H * S), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        mw, mh = 340 * S, 170 * S
        mx = WIN_W * S // 2 - mw // 2
        my = WIN_H * S // 2 - mh // 2
        modal_rect = pygame.Rect(mx, my, mw, mh)
        pygame.draw.rect(surface, C_PANEL_BG, modal_rect, border_radius=12 * S)
        pygame.draw.rect(surface, C_GOLD, modal_rect, max(1, 2 * S), border_radius=12 * S)

        font_big = self.fonts.get(20, bold=True)
        font_normal = self.fonts.get(13)
        font_btn = self.fonts.get(14, bold=True)

        t = font_big.render(self.win_text, True, C_GOLD)
        surface.blit(t, (mx + mw // 2 - t.get_width() // 2, my + 28 * S))

        rounds = self.game.turn_number // 2 + 1
        t = font_normal.render(f"经过 {rounds} 回合的精彩对弈", True, C_TEXT_DIM)
        surface.blit(t, (mx + mw // 2 - t.get_width() // 2, my + 66 * S))

        btn_rect = pygame.Rect(mx + mw // 2 - 55 * S, my + 110 * S, 110 * S, 34 * S)
        pygame.draw.rect(surface, C_GOLD, btn_rect, border_radius=8 * S)
        t = font_btn.render('再来一局', True, C_BG)
        surface.blit(t, (btn_rect.centerx - t.get_width() // 2, btn_rect.centery - t.get_height() // 2))
        self._win_btn_rect = btn_rect

    # ============================================================
    # 绘制：操作提示
    # ============================================================
    def draw_action_prompt(self, surface):
        if not self.action_prompt:
            return
        S = self.S
        font_normal = self.fonts.get(12)
        font_btn = self.fonts.get(12, bold=True)

        bar_h = 44 * S
        bar_rect = pygame.Rect(0, BOARD_H * S - bar_h - 2 * S, BOARD_W * S, bar_h)
        pygame.draw.rect(surface, (42, 26, 14), bar_rect)
        pygame.draw.rect(surface, C_GOLD, bar_rect, max(1, S))

        prompt_text = f"{self.action_prompt['title']}：{self.action_prompt['desc']}"
        t = font_normal.render(prompt_text, True, C_TEXT)
        surface.blit(t, (10 * S, bar_rect.y + 4 * S))

        btn_y = bar_rect.y + 23 * S
        confirm_rect = pygame.Rect(BOARD_W * S // 2 - 100 * S, btn_y, 80 * S, 18 * S)
        skip_rect = pygame.Rect(BOARD_W * S // 2 + 20 * S, btn_y, 80 * S, 18 * S)

        pygame.draw.rect(surface, C_GOLD, confirm_rect, border_radius=4 * S)
        t = font_btn.render('确认', True, C_BG)
        surface.blit(t, (confirm_rect.centerx - t.get_width() // 2, confirm_rect.centery - t.get_height() // 2))

        pygame.draw.rect(surface, (68, 68, 68), skip_rect, border_radius=4 * S)
        t = font_btn.render('跳过', True, C_TEXT)
        surface.blit(t, (skip_rect.centerx - t.get_width() // 2, skip_rect.centery - t.get_height() // 2))

        self._prompt_confirm_rect = confirm_rect
        self._prompt_skip_rect = skip_rect

    # ============================================================
    # 游戏逻辑
    # ============================================================
    def start_game(self):
        for pid, idx in self.rune_selections.items():
            p = self.game.piece_by_id(pid)
            if p:
                opts = RUNE_OPTIONS.get(p.type, [Rune.NONE])
                if idx < len(opts):
                    p.rune = opts[idx]

        if self.game_mode == 'pve':
            ChessAI.choose_runes_for_side(self.game, self.ai_side)
            self.ai_instance = ChessAI(self.ai_side, self.ai_difficulty)
            diff_names = {'easy': '简单', 'normal': '中等', 'hard': '困难'}
            side_name = '红' if self.ai_side == Side.RED else '黑'
            self.add_log(f"AI 执{side_name}（{diff_names[self.ai_difficulty]}）")
        else:
            self.ai_instance = None

        self.game.apply_youmu_swaps()
        self.game.apply_xunying_positions()
        self.game.phase = 'playing'
        self.phase = 'playing'

        if self.game_mode == 'pve' and self.ai_side == Side.RED:
            self._trigger_ai_move()

    def restart_game(self):
        self.game = GameState()
        self.game.init_board()
        self.phase = 'setup'
        self.selected_piece = None
        self.legal_moves = []
        self.highlight_cells = []
        self.hover_piece = None
        self.ai_thinking = False
        self.ai_instance = None
        self.ai_result = None
        self.log_lines = []
        self.show_win_modal = False
        self.action_prompt = None
        self.anim = Animation()
        self.panel_tab = 'info'
        self._init_setup_ui()

    def add_log(self, text):
        self.log_lines.append(text)

    def log_move(self, record):
        p = record.piece
        side = '红' if p.side == Side.RED else '黑'
        text = f"[{side}] {p.name} ({record.from_pos[0]},{record.from_pos[1]})->({record.to_pos[0]},{record.to_pos[1]})"
        if record.captured:
            names = ','.join(c.name for c in record.captured)
            text += f" 吃{names}"
        specials = {
            'doujiang': '斗将', 'xianzhen_charge': '陷阵', 'dujun_cross': '督军过河',
            'congquan': '从权', 'hengxing': '横行', 'jinwei_double': '近卫',
            'yezhan_free': '野战',
        }
        if record.special and record.special in specials:
            text += ' ' + specials[record.special]
        self.add_log(text)

    def select_piece(self, piece):
        self.selected_piece = piece
        self.legal_moves = self.game.get_legal_moves(piece)
        self.highlight_cells = []
        for m in self.legal_moves:
            is_cap = m.captured is not None or m.special == 'xianzhen_charge'
            self.highlight_cells.append({'col': m.col, 'row': m.row, 'type': 'capture' if is_cap else 'move'})

    def do_move_with_anim(self, piece, move):
        fx = self.board_x(piece.col)
        fy = self.board_y(piece.row)
        tx = self.board_x(move.col)
        ty = self.board_y(move.row)

        def on_anim_done():
            result = self.game.execute_move(piece, move)
            if not result:
                return
            self.log_move(result)

            if result.captured:
                self.anim.start_flash(result.captured)
                for cp in result.captured:
                    self.anim.add_particles(
                        self.board_x(cp.col) if cp.alive else tx,
                        self.board_y(cp.row) if cp.alive else ty,
                        (255, 80, 80) if cp.side == Side.RED else (180, 180, 180),
                        count=15
                    )

            self.selected_piece = None
            self.legal_moves = []
            self.highlight_cells = []

            if self.game.pending_luexi_move:
                che = self.game.pending_luexi_move['che']
                self.action_prompt = {
                    'title': '掠袭',
                    'desc': f'{che.name} 可再移动最多3格',
                    'on_confirm': lambda: None,
                    'on_skip': self._skip_luexi,
                }
                return

            if self.game.pending_guaizi_reaction:
                gr = self.game.pending_guaizi_reaction
                self.action_prompt = {
                    'title': '拐子马',
                    'desc': f"{gr['trigger_ma'].name} 可反击 {gr['capturer'].name}",
                    'on_confirm': lambda: self._confirm_guaizi(),
                    'on_skip': lambda: self._skip_guaizi(),
                }
                return

            if self.game.phase == 'ended':
                self._show_win()
                return

            self._check_ai_turn()

        self.anim.start_move(piece, fx, fy, tx, ty, on_anim_done)

    def _skip_luexi(self):
        self.game.skip_luexi_move()
        self.action_prompt = None
        if self.game.phase == 'ended':
            self._show_win()
        else:
            self._check_ai_turn()

    def _confirm_guaizi(self):
        gr = self.game.pending_guaizi_reaction
        self.game.execute_guaizi_reaction(True)
        self.add_log("拐子马反击！")
        self.action_prompt = None
        self.anim.add_particles(
            self.board_x(gr['capture_pos'][0]),
            self.board_y(gr['capture_pos'][1]),
            (255, 200, 50), count=20
        )
        if self.game.phase == 'ended':
            self._show_win()
        else:
            self._check_ai_turn()

    def _skip_guaizi(self):
        self.game.execute_guaizi_reaction(False)
        self.action_prompt = None
        if self.game.phase == 'ended':
            self._show_win()
        else:
            self._check_ai_turn()

    def _show_win(self):
        name = '红方' if self.game.winner == Side.RED else '黑方'
        self.win_text = f"{name}胜利！"
        self.show_win_modal = True

    # ============================================================
    # AI
    # ============================================================
    def _check_ai_turn(self):
        if self.game_mode != 'pve' or not self.ai_instance:
            return
        if self.game.phase != 'playing':
            return
        if self.game.current_side != self.ai_side:
            return
        if self.game.pending_luexi_move or self.game.pending_guaizi_reaction:
            return
        self._trigger_ai_move()

    def _trigger_ai_move(self):
        self.ai_thinking = True
        self.ai_result = None

        def ai_work():
            try:
                result = self.ai_instance.get_best_move(self.game)
                self.ai_result = result
            except Exception as e:
                print(f"AI error: {e}")
                moves = self.game.get_all_legal_moves(self.ai_side)
                if moves:
                    self.ai_result = random.choice(moves)
                else:
                    self.ai_result = None

        self.ai_thread = threading.Thread(target=ai_work, daemon=True)
        self.ai_thread.start()

    def _process_ai_result(self):
        if not self.ai_thinking or self.ai_result is None:
            return
        if self.ai_thread and self.ai_thread.is_alive():
            return
        if self.anim.active:
            return

        self.ai_thinking = False
        best = self.ai_result
        self.ai_result = None

        if best:
            piece, move = best
            actual_piece = self.game.piece_by_id(piece.id)
            if actual_piece:
                actual_move = self._remap_move(move)
                self.do_move_with_anim(actual_piece, actual_move)
            else:
                moves = self.game.get_all_legal_moves(self.ai_side)
                if moves:
                    p, m = random.choice(moves)
                    self.do_move_with_anim(p, m)

    def _remap_move(self, move):
        m = Move(move.col, move.row, move.type, special=move.special)
        if move.captured:
            m.captured = self.game.piece_by_id(move.captured.id)
        if move.captured_multi:
            m.captured_multi = [self.game.piece_by_id(cp.id) for cp in move.captured_multi
                                if self.game.piece_by_id(cp.id)]
        if move.destroyed:
            m.destroyed = [self.game.piece_by_id(dp.id) for dp in move.destroyed
                           if self.game.piece_by_id(dp.id)]
        if move.via:
            m.via = dict(move.via)
            if move.via.get('captured'):
                m.via['captured'] = self.game.piece_by_id(move.via['captured'].id)
        return m

    # ============================================================
    # 事件处理
    # ============================================================
    def handle_setup_click(self, mx, my):
        # 窗口尺寸按钮
        for rect, idx in self._size_buttons:
            if rect.collidepoint(mx, my):
                self.set_window_scale(idx)
                return

        for rect, val in self.mode_buttons:
            if rect.collidepoint(mx, my):
                self.game_mode = val
                self.player_side = Side.RED if self.ai_side == Side.BLACK else Side.BLACK
                self._init_setup_ui()
                return

        for rect, val in getattr(self, '_diff_buttons', []):
            if rect.collidepoint(mx, my):
                self.ai_difficulty = val
                return

        for rect, val in getattr(self, '_side_buttons', []):
            if rect.collidepoint(mx, my):
                self.ai_side = Side.RED if val == 'red' else Side.BLACK
                self.player_side = Side.BLACK if self.ai_side == Side.RED else Side.RED
                self._init_setup_ui()
                return

        for btype, rect, pid in self.setup_buttons:
            if not rect.collidepoint(mx, my):
                continue
            if btype == 'rune_left':
                p = self.game.piece_by_id(pid)
                opts = RUNE_OPTIONS.get(p.type, [Rune.NONE])
                idx = self.rune_selections.get(pid, 0)
                self.rune_selections[pid] = (idx - 1) % len(opts)
            elif btype == 'rune_right':
                p = self.game.piece_by_id(pid)
                opts = RUNE_OPTIONS.get(p.type, [Rune.NONE])
                idx = self.rune_selections.get(pid, 0)
                self.rune_selections[pid] = (idx + 1) % len(opts)
            elif btype == 'random':
                self._random_runes()
            elif btype == 'start':
                self.start_game()
            return

    def _random_runes(self):
        for pid in self.rune_selections:
            p = self.game.piece_by_id(pid)
            if p:
                opts = RUNE_OPTIONS.get(p.type, [Rune.NONE])
                self.rune_selections[pid] = random.randint(0, len(opts) - 1)

    def handle_game_click(self, mx, my):
        # 窗口尺寸按钮（在面板底部）
        for rect, idx in self._size_buttons:
            if rect.collidepoint(mx, my):
                self.set_window_scale(idx)
                return

        if self.game.phase != 'playing':
            return
        if self.anim.active:
            return
        if self.ai_thinking:
            return
        if self.game_mode == 'pve' and self.game.current_side == self.ai_side:
            if not self.game.pending_luexi_move and not self.game.pending_guaizi_reaction:
                return

        # Tab 切换
        if hasattr(self, '_tab_info_rect') and self._tab_info_rect.collidepoint(mx, my):
            self.panel_tab = 'info'
            return
        if hasattr(self, '_tab_rune_rect') and self._tab_rune_rect.collidepoint(mx, my):
            self.panel_tab = 'runes'
            return

        # 操作提示按钮
        if self.action_prompt:
            if hasattr(self, '_prompt_confirm_rect') and self._prompt_confirm_rect.collidepoint(mx, my):
                self.action_prompt['on_confirm']()
                return
            if hasattr(self, '_prompt_skip_rect') and self._prompt_skip_rect.collidepoint(mx, my):
                self.action_prompt['on_skip']()
                return

        # 重启按钮
        if hasattr(self, '_restart_btn_rect') and self._restart_btn_rect.collidepoint(mx, my):
            self.restart_game()
            return

        col, row = self.screen_to_board(mx, my)
        if col is None:
            return

        # 掠袭二次移动
        if self.game.pending_luexi_move:
            che = self.game.pending_luexi_move['che']
            old_col, old_row = che.col, che.row
            if self.game.execute_luexi_move(che, col, row):
                self.action_prompt = None
                self.add_log(f"{che.name} 掠袭追击至 ({col},{row})")
                fx = self.board_x(old_col)
                fy = self.board_y(old_row)
                tx = self.board_x(col)
                ty = self.board_y(row)
                self.anim.start_move(che, fx, fy, tx, ty, lambda: self._check_ai_turn())
                self.selected_piece = None
                self.legal_moves = []
                self.highlight_cells = []
            return

        clicked_piece = self.game.piece_at(col, row)

        if self.selected_piece:
            move = next((m for m in self.legal_moves if m.col == col and m.row == row), None)
            if move:
                self.do_move_with_anim(self.selected_piece, move)
                return
            if clicked_piece and clicked_piece.side == self.game.current_side:
                self.select_piece(clicked_piece)
                return
            self.selected_piece = None
            self.legal_moves = []
            self.highlight_cells = []
            return

        if clicked_piece and clicked_piece.side == self.game.current_side:
            self.select_piece(clicked_piece)

    def handle_mouse_move(self, mx, my):
        self.mouse_pos = (mx, my)
        if self.phase != 'playing':
            return
        col, row = self.screen_to_board(mx, my)
        new_hover = None
        if col is not None:
            new_hover = self.game.piece_at(col, row)

        if new_hover != self.hover_piece:
            self.hover_piece = new_hover
            self.tooltip_piece = new_hover
            self.tooltip_show_time = time.time()
        elif new_hover is None:
            self.tooltip_piece = None

    # ============================================================
    # 主循环
    # ============================================================
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    lx, ly = self._screen_to_logical(*event.pos)
                    if self.show_win_modal:
                        if hasattr(self, '_win_btn_rect') and self._win_btn_rect.collidepoint(lx, ly):
                            self.restart_game()
                    elif self.phase == 'setup':
                        self.handle_setup_click(lx, ly)
                    elif self.phase == 'playing':
                        self.handle_game_click(lx, ly)
                elif event.type == pygame.MOUSEMOTION:
                    lx, ly = self._screen_to_logical(*event.pos)
                    self.handle_mouse_move(lx, ly)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.show_win_modal:
                            self.restart_game()

            self.anim.update(dt)

            if self.ai_thinking and self.ai_result is not None:
                self._process_ai_result()

            # 绘制到离屏高分辨率画布
            self.canvas.fill(C_BG)
            if self.phase == 'setup':
                self.draw_setup(self.canvas)
            else:
                self.draw_board(self.canvas)
                self.draw_highlights(self.canvas)
                self.draw_luexi_range(self.canvas)
                self.draw_pieces(self.canvas)
                self.draw_particles(self.canvas)
                self.draw_panel(self.canvas)
                self.draw_action_prompt(self.canvas)
                self.draw_tooltip(self.canvas)
                self.draw_win_modal(self.canvas)

            # smoothscale 到窗口大小并显示
            if (self.canvas_w, self.canvas_h) != (self.win_w, self.win_h):
                scaled = pygame.transform.smoothscale(self.canvas, (self.win_w, self.win_h))
                self.screen.blit(scaled, (0, 0))
            else:
                self.screen.blit(self.canvas, (0, 0))

            pygame.display.flip()

        pygame.quit()


if __name__ == '__main__':
    game = ChessGame()
    game.run()
