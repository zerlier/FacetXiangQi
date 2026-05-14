"""
命石象棋 - 核心引擎
"""
import copy
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

# ============================================================
# 枚举定义
# ============================================================
class PieceType(str, Enum):
    JIANG = 'jiang'
    SHI = 'shi'
    XIANG = 'xiang'
    MA = 'ma'
    CHE = 'che'
    PAO = 'pao'
    BING = 'bing'

class Side(str, Enum):
    RED = 'red'
    BLACK = 'black'

class Rune(str, Enum):
    NONE = 'none'
    BING_XIANZHEN = 'bing_xianzhen'
    BING_WEIBING = 'bing_weibing'
    BING_FUBING = 'bing_fubing'
    PAO_YEZHAN = 'pao_yezhan'
    PAO_ZHONGPAO = 'pao_zhongpao'
    SHI_JINWEI = 'shi_jinwei'
    SHI_XUNYING = 'shi_xunying'
    JIANG_DOUJIANG = 'jiang_doujiang'
    JIANG_SUJIANG = 'jiang_sujiang'
    XIANG_DUJUN = 'xiang_dujun'
    XIANG_CONGQUAN = 'xiang_congquan'
    MA_QINGQI = 'ma_qingqi'
    MA_YOUMU = 'ma_youmu'
    MA_GUAIZI = 'ma_guaizi'
    CHE_LUEXI = 'che_luexi'
    CHE_HENGXING = 'che_hengxing'

# 命石可选列表
RUNE_OPTIONS = {
    PieceType.BING:  [Rune.NONE, Rune.BING_XIANZHEN, Rune.BING_WEIBING, Rune.BING_FUBING],
    PieceType.PAO:   [Rune.NONE, Rune.PAO_YEZHAN, Rune.PAO_ZHONGPAO],
    PieceType.SHI:   [Rune.NONE, Rune.SHI_JINWEI, Rune.SHI_XUNYING],
    PieceType.JIANG: [Rune.NONE, Rune.JIANG_DOUJIANG, Rune.JIANG_SUJIANG],
    PieceType.XIANG: [Rune.NONE, Rune.XIANG_DUJUN, Rune.XIANG_CONGQUAN],
    PieceType.MA:    [Rune.NONE, Rune.MA_QINGQI, Rune.MA_YOUMU, Rune.MA_GUAIZI],
    PieceType.CHE:   [Rune.NONE, Rune.CHE_LUEXI, Rune.CHE_HENGXING],
}

RUNE_NAMES = {
    Rune.NONE: '无', Rune.BING_XIANZHEN: '陷阵', Rune.BING_WEIBING: '卫兵',
    Rune.BING_FUBING: '伏兵', Rune.PAO_YEZHAN: '野战炮', Rune.PAO_ZHONGPAO: '重炮',
    Rune.SHI_JINWEI: '近卫', Rune.SHI_XUNYING: '巡营', Rune.JIANG_DOUJIANG: '斗将',
    Rune.JIANG_SUJIANG: '宿将', Rune.XIANG_DUJUN: '督军', Rune.XIANG_CONGQUAN: '事急从权',
    Rune.MA_QINGQI: '轻骑', Rune.MA_YOUMU: '游牧佣军', Rune.MA_GUAIZI: '拐子马',
    Rune.CHE_LUEXI: '掠袭', Rune.CHE_HENGXING: '横行',
}

RUNE_DESCS = {
    Rune.NONE: '不使用任何命石',
    Rune.BING_XIANZHEN: '可向前突进两格取代通常移动，吃掉经过的所有敌方棋子（不可穿过友军）',
    Rune.BING_WEIBING: '不再能移动过河，但在过河前即可进行左右移动（仍不可后退）',
    Rune.BING_FUBING: '本方前8回合内若未移动过，被吃时吃子的敌方棋子也一起阵亡（同归于尽）',
    Rune.PAO_YEZHAN: '前三次移动不能吃子，但本场可不需要炮架吃子一次',
    Rune.PAO_ZHONGPAO: '吃子时同时消灭目标身后一格的敌方棋子。吃子后下一轮不能行动',
    Rune.SHI_JINWEI: '不再斜走，单次行动可在同一方向移动至多2次每次1格（仅能吃子一次）',
    Rune.SHI_XUNYING: '出生点改为九宫格顶角，可以离开九宫格但不能过河',
    Rune.JIANG_DOUJIANG: '若与敌将之间仅有己方棋子阻拦，可消耗一步吃掉对面的将',
    Rune.JIANG_SUJIANG: '在被消灭将与任一个相之后才会失败',
    Rune.XIANG_DUJUN: '抵达河边时可消耗一步前往对岸对应位置，该移动可以吃子',
    Rune.XIANG_CONGQUAN: '可以往前一步取代相平时的移动方式，该特殊移动不可吃子',
    Rune.MA_QINGQI: '不再会被拌马腿，但不能吃车',
    Rune.MA_YOUMU: '开局与相邻的己方车互换位置，在损失掉己方所有车之前不可移动',
    Rune.MA_GUAIZI: '己方马或兵在其攻击范围内被吃时，可免费行动一次消灭吃子的敌方棋子',
    Rune.CHE_LUEXI: '吃子前至少移动6格，则吃子后可再移动最多3格（不可吃子）',
    Rune.CHE_HENGXING: '可越过己方棋子攻击敌方棋子，但消灭路过的所有己方棋子',
}

PIECE_NAMES = {
    Side.RED: {PieceType.JIANG:'帅', PieceType.SHI:'仕', PieceType.XIANG:'相',
               PieceType.MA:'馬', PieceType.CHE:'車', PieceType.PAO:'炮', PieceType.BING:'兵'},
    Side.BLACK: {PieceType.JIANG:'将', PieceType.SHI:'士', PieceType.XIANG:'象',
                 PieceType.MA:'马', PieceType.CHE:'车', PieceType.PAO:'砲', PieceType.BING:'卒'},
}

# ============================================================
# Move 数据结构
# ============================================================
@dataclass
class Move:
    col: int
    row: int
    type: str = 'move'  # move | capture
    captured: Optional['Piece'] = None
    captured_multi: Optional[List['Piece']] = None
    destroyed: Optional[List['Piece']] = None
    special: Optional[str] = None
    via: Optional[Dict] = None  # {col, row, captured}

# ============================================================
# Piece
# ============================================================
_piece_id_counter = 0

class Piece:
    def __init__(self, ptype: PieceType, side: Side, col: int, row: int):
        global _piece_id_counter
        _piece_id_counter += 1
        self.id = _piece_id_counter
        self.type = ptype
        self.side = side
        self.col = col
        self.row = row
        self.rune = Rune.NONE
        self.alive = True
        self.move_count = 0
        self.has_moved = False
        self.stun_next_turn = False
        self.yezhan_used = False
        self.last_move_distance = 0
        self.youmu_swapped = False

    @property
    def name(self):
        return PIECE_NAMES[self.side][self.type]

    @property
    def rune_name(self):
        return RUNE_NAMES[self.rune]

    def clone(self):
        p = Piece.__new__(Piece)
        p.id = self.id
        p.type = self.type
        p.side = self.side
        p.col = self.col
        p.row = self.row
        p.rune = self.rune
        p.alive = self.alive
        p.move_count = self.move_count
        p.has_moved = self.has_moved
        p.stun_next_turn = self.stun_next_turn
        p.yezhan_used = self.yezhan_used
        p.last_move_distance = self.last_move_distance
        p.youmu_swapped = self.youmu_swapped
        return p

# ============================================================
# MoveRecord
# ============================================================
@dataclass
class MoveRecord:
    piece: Piece
    from_pos: Tuple[int, int]
    to_pos: Tuple[int, int]
    captured: List[Piece] = field(default_factory=list)
    special: Optional[str] = None

# ============================================================
# GameState
# ============================================================
class GameState:
    def __init__(self):
        self.pieces: List[Piece] = []
        self.current_side = Side.RED
        self.turn_number = 0
        self.phase = 'setup'  # setup | playing | ended
        self.winner = None
        self.move_history: List[MoveRecord] = []
        self.pending_guaizi_reaction = None
        self.pending_luexi_move = None
        self.sujiang_active = {Side.RED: False, Side.BLACK: False}

    def init_board(self):
        global _piece_id_counter
        _piece_id_counter = 0
        self.pieces = []
        red_layout = [
            (PieceType.CHE,0,0),(PieceType.MA,1,0),(PieceType.XIANG,2,0),
            (PieceType.SHI,3,0),(PieceType.JIANG,4,0),(PieceType.SHI,5,0),
            (PieceType.XIANG,6,0),(PieceType.MA,7,0),(PieceType.CHE,8,0),
            (PieceType.PAO,1,2),(PieceType.PAO,7,2),
            (PieceType.BING,0,3),(PieceType.BING,2,3),(PieceType.BING,4,3),
            (PieceType.BING,6,3),(PieceType.BING,8,3),
        ]
        black_layout = [
            (PieceType.CHE,0,9),(PieceType.MA,1,9),(PieceType.XIANG,2,9),
            (PieceType.SHI,3,9),(PieceType.JIANG,4,9),(PieceType.SHI,5,9),
            (PieceType.XIANG,6,9),(PieceType.MA,7,9),(PieceType.CHE,8,9),
            (PieceType.PAO,1,7),(PieceType.PAO,7,7),
            (PieceType.BING,0,6),(PieceType.BING,2,6),(PieceType.BING,4,6),
            (PieceType.BING,6,6),(PieceType.BING,8,6),
        ]
        for t, c, r in red_layout:
            self.pieces.append(Piece(t, Side.RED, c, r))
        for t, c, r in black_layout:
            self.pieces.append(Piece(t, Side.BLACK, c, r))

    def apply_youmu_swaps(self):
        for ma in [p for p in self.alive_pieces() if p.type == PieceType.MA and p.rune == Rune.MA_YOUMU]:
            adj = [p for p in self.alive_pieces()
                   if p.type == PieceType.CHE and p.side == ma.side
                   and abs(p.col - ma.col) + abs(p.row - ma.row) == 1]
            if adj:
                che = adj[0]
                ma.col, ma.row, che.col, che.row = che.col, che.row, ma.col, ma.row
                ma.youmu_swapped = True

    def apply_xunying_positions(self):
        for shi in [p for p in self.alive_pieces() if p.type == PieceType.SHI and p.rune == Rune.SHI_XUNYING]:
            if shi.side == Side.RED:
                if shi.row == 0 and shi.col in (3, 5):
                    shi.row = 2
            else:
                if shi.row == 9 and shi.col in (3, 5):
                    shi.row = 7

    def alive_pieces(self, side=None) -> List[Piece]:
        return [p for p in self.pieces if p.alive and (side is None or p.side == side)]

    def piece_at(self, col, row) -> Optional[Piece]:
        for p in self.alive_pieces():
            if p.col == col and p.row == row:
                return p
        return None

    def piece_by_id(self, pid) -> Optional[Piece]:
        for p in self.pieces:
            if p.id == pid:
                return p
        return None

    @staticmethod
    def is_in_board(col, row):
        return 0 <= col <= 8 and 0 <= row <= 9

    def is_crossed_river(self, piece):
        return piece.row >= 5 if piece.side == Side.RED else piece.row <= 4

    @staticmethod
    def is_in_palace(col, row, side):
        if side == Side.RED:
            return 3 <= col <= 5 and 0 <= row <= 2
        return 3 <= col <= 5 and 7 <= row <= 9

    def pieces_between(self, c1, r1, c2, r2) -> List[Piece]:
        result = []
        if c1 == c2:
            lo, hi = (min(r1, r2) + 1, max(r1, r2))
            for r in range(lo, hi):
                p = self.piece_at(c1, r)
                if p:
                    result.append(p)
        elif r1 == r2:
            lo, hi = (min(c1, c2) + 1, max(c1, c2))
            for c in range(lo, hi):
                p = self.piece_at(c, r1)
                if p:
                    result.append(p)
        return result

    # ============================================================
    # 合法移动生成
    # ============================================================
    def get_legal_moves(self, piece) -> List[Move]:
        if not piece.alive:
            return []
        if piece.stun_next_turn:
            return []
        # 游牧佣军
        if piece.rune == Rune.MA_YOUMU:
            ally_che = [p for p in self.alive_pieces(piece.side) if p.type == PieceType.CHE]
            if ally_che:
                return []

        dispatch = {
            PieceType.JIANG: self._jiang_moves,
            PieceType.SHI: self._shi_moves,
            PieceType.XIANG: self._xiang_moves,
            PieceType.MA: self._ma_moves,
            PieceType.CHE: self._che_moves,
            PieceType.PAO: self._pao_moves,
            PieceType.BING: self._bing_moves,
        }
        return dispatch[piece.type](piece)

    def _jiang_moves(self, p):
        moves = []
        for dc, dr in [(0,1),(0,-1),(1,0),(-1,0)]:
            nc, nr = p.col + dc, p.row + dr
            if not self.is_in_palace(nc, nr, p.side):
                continue
            t = self.piece_at(nc, nr)
            if t and t.side == p.side:
                continue
            moves.append(Move(nc, nr, 'capture' if t else 'move', captured=t))
        # 斗将
        if p.rune == Rune.JIANG_DOUJIANG:
            ej = next((ep for ep in self.alive_pieces() if ep.type == PieceType.JIANG and ep.side != p.side), None)
            if ej and ej.col == p.col:
                between = self.pieces_between(p.col, p.row, ej.col, ej.row)
                if between and all(bp.side == p.side for bp in between):
                    moves.append(Move(ej.col, ej.row, 'capture', captured=ej, special='doujiang'))
        return moves

    def _shi_moves(self, p):
        moves = []
        if p.rune == Rune.SHI_JINWEI:
            for dc, dr in [(0,1),(0,-1),(1,0),(-1,0)]:
                nc1, nr1 = p.col + dc, p.row + dr
                if not self.is_in_palace(nc1, nr1, p.side):
                    continue
                t1 = self.piece_at(nc1, nr1)
                if t1 and t1.side == p.side:
                    continue
                moves.append(Move(nc1, nr1, 'capture' if t1 else 'move', captured=t1))
                nc2, nr2 = nc1 + dc, nr1 + dr
                if not self.is_in_palace(nc2, nr2, p.side):
                    continue
                t2 = self.piece_at(nc2, nr2)
                if t2 and t2.side == p.side:
                    continue
                if t1:
                    if t2:
                        continue
                    moves.append(Move(nc2, nr2, 'move', special='jinwei_double',
                                      via={'col': nc1, 'row': nr1, 'captured': t1}))
                else:
                    if t2 and t2.side == p.side:
                        continue
                    moves.append(Move(nc2, nr2, 'capture' if t2 else 'move', captured=t2,
                                      special='jinwei_double', via={'col': nc1, 'row': nr1, 'captured': None}))
        elif p.rune == Rune.SHI_XUNYING:
            for dc, dr in [(1,1),(1,-1),(-1,1),(-1,-1)]:
                nc, nr = p.col + dc, p.row + dr
                if not self.is_in_board(nc, nr):
                    continue
                if p.side == Side.RED and nr >= 5:
                    continue
                if p.side == Side.BLACK and nr <= 4:
                    continue
                t = self.piece_at(nc, nr)
                if t and t.side == p.side:
                    continue
                moves.append(Move(nc, nr, 'capture' if t else 'move', captured=t))
        else:
            for dc, dr in [(1,1),(1,-1),(-1,1),(-1,-1)]:
                nc, nr = p.col + dc, p.row + dr
                if not self.is_in_palace(nc, nr, p.side):
                    continue
                t = self.piece_at(nc, nr)
                if t and t.side == p.side:
                    continue
                moves.append(Move(nc, nr, 'capture' if t else 'move', captured=t))
        return moves

    def _xiang_moves(self, p):
        moves = []
        for dc, dr in [(2,2),(2,-2),(-2,2),(-2,-2)]:
            nc, nr = p.col + dc, p.row + dr
            if not self.is_in_board(nc, nr):
                continue
            if p.side == Side.RED and nr >= 5:
                continue
            if p.side == Side.BLACK and nr <= 4:
                continue
            eye_c, eye_r = p.col + dc // 2, p.row + dr // 2
            if self.piece_at(eye_c, eye_r):
                continue
            t = self.piece_at(nc, nr)
            if t and t.side == p.side:
                continue
            moves.append(Move(nc, nr, 'capture' if t else 'move', captured=t))
        # 督军
        if p.rune == Rune.XIANG_DUJUN:
            river_row = 4 if p.side == Side.RED else 5
            if p.row == river_row:
                target_row = 5 if p.side == Side.RED else 4
                t = self.piece_at(p.col, target_row)
                if not t or t.side != p.side:
                    moves.append(Move(p.col, target_row, 'capture' if t else 'move',
                                      captured=t, special='dujun_cross'))
        # 事急从权
        if p.rune == Rune.XIANG_CONGQUAN:
            fwd = 1 if p.side == Side.RED else -1
            nr = p.row + fwd
            if self.is_in_board(p.col, nr):
                if not (p.side == Side.RED and nr >= 5) and not (p.side == Side.BLACK and nr <= 4):
                    if not self.piece_at(p.col, nr):
                        moves.append(Move(p.col, nr, 'move', special='congquan'))
        return moves

    def _ma_moves(self, p):
        moves = []
        jumps = [(1,2,0,1),(1,-2,0,-1),(-1,2,0,1),(-1,-2,0,-1),
                 (2,1,1,0),(2,-1,1,0),(-2,1,-1,0),(-2,-1,-1,0)]
        for dc, dr, bc, br in jumps:
            nc, nr = p.col + dc, p.row + dr
            if not self.is_in_board(nc, nr):
                continue
            if p.rune != Rune.MA_QINGQI:
                if self.piece_at(p.col + bc, p.row + br):
                    continue
            t = self.piece_at(nc, nr)
            if t and t.side == p.side:
                continue
            if p.rune == Rune.MA_QINGQI and t and t.type == PieceType.CHE:
                continue
            moves.append(Move(nc, nr, 'capture' if t else 'move', captured=t))
        return moves

    def _che_moves(self, p):
        moves = []
        for dc, dr in [(0,1),(0,-1),(1,0),(-1,0)]:
            for i in range(1, 10):
                nc, nr = p.col + dc * i, p.row + dr * i
                if not self.is_in_board(nc, nr):
                    break
                t = self.piece_at(nc, nr)
                if t:
                    if t.side == p.side:
                        if p.rune == Rune.CHE_HENGXING:
                            friendlies = [t]
                            for j in range(i + 1, 10):
                                nc2, nr2 = p.col + dc * j, p.row + dr * j
                                if not self.is_in_board(nc2, nr2):
                                    break
                                t2 = self.piece_at(nc2, nr2)
                                if t2:
                                    if t2.side != p.side:
                                        moves.append(Move(nc2, nr2, 'capture', captured=t2,
                                                          special='hengxing', destroyed=list(friendlies)))
                                    elif t2.side == p.side:
                                        friendlies.append(t2)
                                        continue
                                    break
                        break
                    moves.append(Move(nc, nr, 'capture', captured=t))
                    break
                moves.append(Move(nc, nr, 'move'))
        return moves

    def _pao_moves(self, p):
        moves = []
        is_yezhan = p.rune == Rune.PAO_YEZHAN
        yezhan_no_cap = is_yezhan and p.move_count < 3
        yezhan_free = is_yezhan and not p.yezhan_used

        for dc, dr in [(0,1),(0,-1),(1,0),(-1,0)]:
            screen = 0
            for i in range(1, 10):
                nc, nr = p.col + dc * i, p.row + dr * i
                if not self.is_in_board(nc, nr):
                    break
                t = self.piece_at(nc, nr)
                if t:
                    if screen == 0:
                        if yezhan_free and not yezhan_no_cap and t.side != p.side:
                            moves.append(Move(nc, nr, 'capture', captured=t, special='yezhan_free'))
                        screen += 1
                    elif screen == 1:
                        if t.side != p.side and not yezhan_no_cap:
                            moves.append(Move(nc, nr, 'capture', captured=t))
                        break
                else:
                    if screen == 0:
                        moves.append(Move(nc, nr, 'move'))
        return moves

    def _bing_moves(self, p):
        moves = []
        fwd = 1 if p.side == Side.RED else -1
        crossed = self.is_crossed_river(p)

        if p.rune == Rune.BING_WEIBING:
            if not crossed:
                nr = p.row + fwd
                if self.is_in_board(p.col, nr):
                    would_cross = (p.side == Side.RED and nr >= 5) or (p.side == Side.BLACK and nr <= 4)
                    if not would_cross:
                        t = self.piece_at(p.col, nr)
                        if not t or t.side != p.side:
                            moves.append(Move(p.col, nr, 'capture' if t else 'move', captured=t))
                for dc in (-1, 1):
                    nc = p.col + dc
                    if self.is_in_board(nc, p.row):
                        t = self.piece_at(nc, p.row)
                        if not t or t.side != p.side:
                            moves.append(Move(nc, p.row, 'capture' if t else 'move', captured=t))
            else:
                nr = p.row + fwd
                if self.is_in_board(p.col, nr):
                    t = self.piece_at(p.col, nr)
                    if not t or t.side != p.side:
                        moves.append(Move(p.col, nr, 'capture' if t else 'move', captured=t))
                for dc in (-1, 1):
                    nc = p.col + dc
                    if self.is_in_board(nc, p.row):
                        t = self.piece_at(nc, p.row)
                        if not t or t.side != p.side:
                            moves.append(Move(nc, p.row, 'capture' if t else 'move', captured=t))
        elif p.rune == Rune.BING_XIANZHEN:
            if crossed:
                nr = p.row + fwd
                if self.is_in_board(p.col, nr):
                    t = self.piece_at(p.col, nr)
                    if not t or t.side != p.side:
                        moves.append(Move(p.col, nr, 'capture' if t else 'move', captured=t))
                for dc in (-1, 1):
                    nc = p.col + dc
                    if self.is_in_board(nc, p.row):
                        t = self.piece_at(nc, p.row)
                        if not t or t.side != p.side:
                            moves.append(Move(nc, p.row, 'capture' if t else 'move', captured=t))
            else:
                nr = p.row + fwd
                if self.is_in_board(p.col, nr):
                    t = self.piece_at(p.col, nr)
                    if not t or t.side != p.side:
                        moves.append(Move(p.col, nr, 'capture' if t else 'move', captured=t))
            # 突进两格
            nr1, nr2 = p.row + fwd, p.row + fwd * 2
            if self.is_in_board(p.col, nr2):
                mid = self.piece_at(p.col, nr1)
                end = self.piece_at(p.col, nr2)
                if not (mid and mid.side == p.side):
                    if not end or end.side != p.side:
                        cap_multi = []
                        if mid and mid.side != p.side:
                            cap_multi.append(mid)
                        if end and end.side != p.side:
                            cap_multi.append(end)
                        moves.append(Move(p.col, nr2, 'move', special='xianzhen_charge',
                                          captured_multi=cap_multi))
        else:
            if crossed:
                nr = p.row + fwd
                if self.is_in_board(p.col, nr):
                    t = self.piece_at(p.col, nr)
                    if not t or t.side != p.side:
                        moves.append(Move(p.col, nr, 'capture' if t else 'move', captured=t))
                for dc in (-1, 1):
                    nc = p.col + dc
                    if self.is_in_board(nc, p.row):
                        t = self.piece_at(nc, p.row)
                        if not t or t.side != p.side:
                            moves.append(Move(nc, p.row, 'capture' if t else 'move', captured=t))
            else:
                nr = p.row + fwd
                if self.is_in_board(p.col, nr):
                    t = self.piece_at(p.col, nr)
                    if not t or t.side != p.side:
                        moves.append(Move(p.col, nr, 'capture' if t else 'move', captured=t))
        return moves

    # ============================================================
    # 执行移动
    # ============================================================
    def execute_move(self, piece, move):
        record = MoveRecord(
            piece=piece,
            from_pos=(piece.col, piece.row),
            to_pos=(move.col, move.row),
            special=move.special,
        )
        # 伏兵检查辅助函数
        def _is_fubing_active(target):
            """判断目标棋子的伏兵效果是否激活：本方前8回合内且未移动过"""
            if target.rune != Rune.BING_FUBING or target.has_moved:
                return False
            # 计算该方已走回合数：红方先手
            if target.side == Side.RED:
                side_turns = (self.turn_number + 1) // 2
            else:
                side_turns = self.turn_number // 2
            return side_turns <= 8

        # 陷阵突进
        if move.special == 'xianzhen_charge' and move.captured_multi:
            for cp in move.captured_multi:
                if _is_fubing_active(cp):
                    # 伏兵同归于尽：伏兵死亡，吃子方也死亡
                    cp.alive = False
                    record.captured.append(cp)
                    piece.alive = False
                    record.captured.append(piece)
                    record.special = 'fubing_mutual'
                    self.move_history.append(record)
                    self.turn_number += 1
                    self.current_side = Side.BLACK if self.current_side == Side.RED else Side.RED
                    self._check_win_condition()
                    return record
                cp.alive = False
                record.captured.append(cp)

        # 横行
        if move.special == 'hengxing' and move.destroyed:
            for fp in move.destroyed:
                fp.alive = False
                record.captured.append(fp)

        # 标准吃子
        if move.captured:
            if _is_fubing_active(move.captured):
                # 伏兵同归于尽：伏兵死亡，吃子方也死亡
                move.captured.alive = False
                record.captured.append(move.captured)
                piece.alive = False
                record.captured.append(piece)
                record.special = 'fubing_mutual'
                # 棋子不移动到目标位置（双方都阵亡）
                self.move_history.append(record)
                self.turn_number += 1
                self.current_side = Side.BLACK if self.current_side == Side.RED else Side.RED
                self._check_win_condition()
                return record
            move.captured.alive = False
            record.captured.append(move.captured)

        # 近卫双步
        if move.special == 'jinwei_double' and move.via and move.via.get('captured'):
            move.via['captured'].alive = False
            record.captured.append(move.via['captured'])

        # 重炮
        if piece.rune == Rune.PAO_ZHONGPAO and move.captured:
            dc = 0 if move.col == piece.col else (1 if move.col > piece.col else -1)
            dr = 0 if move.row == piece.row else (1 if move.row > piece.row else -1)
            bc, br = move.col + dc, move.row + dr
            if self.is_in_board(bc, br):
                behind = self.piece_at(bc, br)
                if behind and behind.side != piece.side:
                    behind.alive = False
                    record.captured.append(behind)
            piece.stun_next_turn = True

        # 野战炮
        if move.special == 'yezhan_free':
            piece.yezhan_used = True

        # 移动棋子
        dist = abs(move.col - piece.col) + abs(move.row - piece.row)
        piece.last_move_distance = dist
        piece.col = move.col
        piece.row = move.row
        piece.move_count += 1
        piece.has_moved = True

        # 掠袭车
        if piece.rune == Rune.CHE_LUEXI and record.captured and dist >= 6:
            self.pending_luexi_move = {'che': piece}

        # 拐子马反击
        self._check_guaizi_reaction(record)
        self.move_history.append(record)
        self.turn_number += 1

        # 清除眩晕
        for pp in self.alive_pieces(piece.side):
            if pp is not piece and pp.stun_next_turn:
                pp.stun_next_turn = False

        # 切换回合
        if not self.pending_luexi_move and not self.pending_guaizi_reaction:
            self.current_side = Side.BLACK if self.current_side == Side.RED else Side.RED

        self._check_win_condition()
        return record

    def execute_luexi_move(self, che, col, row):
        dist = abs(col - che.col) + abs(row - che.row)
        if dist > 3:
            return False
        if self.piece_at(col, row):
            return False
        if col != che.col and row != che.row:
            return False
        between = self.pieces_between(che.col, che.row, col, row)
        if between:
            return False
        che.col = col
        che.row = row
        self.pending_luexi_move = None
        self.current_side = Side.BLACK if self.current_side == Side.RED else Side.RED
        return True

    def skip_luexi_move(self):
        self.pending_luexi_move = None
        self.current_side = Side.BLACK if self.current_side == Side.RED else Side.RED

    def _check_guaizi_reaction(self, record):
        for cp in record.captured:
            if cp.type not in (PieceType.MA, PieceType.BING):
                continue
            guazi_mas = [p for p in self.alive_pieces(cp.side)
                         if p.type == PieceType.MA and p.rune == Rune.MA_GUAIZI]
            for gm in guazi_mas:
                g_moves = self._ma_moves(gm)
                if any(m.col == cp.col and m.row == cp.row for m in g_moves):
                    attack_moves = self._ma_moves(gm)
                    if any(m.col == record.piece.col and m.row == record.piece.row for m in attack_moves):
                        self.pending_guaizi_reaction = {
                            'trigger_ma': gm,
                            'captured_piece': cp,
                            'capturer': record.piece,
                            'capture_pos': (record.piece.col, record.piece.row),
                        }
                        return

    def execute_guaizi_reaction(self, confirm):
        if not self.pending_guaizi_reaction:
            return
        if confirm:
            gr = self.pending_guaizi_reaction
            gr['capturer'].alive = False
            gr['trigger_ma'].col = gr['capture_pos'][0]
            gr['trigger_ma'].row = gr['capture_pos'][1]
        self.pending_guaizi_reaction = None
        self.current_side = Side.BLACK if self.current_side == Side.RED else Side.RED
        self._check_win_condition()

    def _check_win_condition(self):
        for side in (Side.RED, Side.BLACK):
            jiang = next((p for p in self.alive_pieces(side) if p.type == PieceType.JIANG), None)
            if not jiang:
                if self.sujiang_active[side]:
                    xiangs = [p for p in self.alive_pieces(side) if p.type == PieceType.XIANG]
                    if xiangs:
                        continue
                self.phase = 'ended'
                self.winner = Side.BLACK if side == Side.RED else Side.RED
                return
        for side in (Side.RED, Side.BLACK):
            jiang = next((p for p in self.alive_pieces(side) if p.type == PieceType.JIANG), None)
            if jiang and jiang.rune == Rune.JIANG_SUJIANG:
                self.sujiang_active[side] = True

    # ============================================================
    # AI 接口
    # ============================================================
    def get_all_legal_moves(self, side):
        all_moves = []
        for p in self.alive_pieces(side):
            for m in self.get_legal_moves(p):
                all_moves.append((p, m))
        return all_moves

    def deep_clone(self):
        gs = GameState()
        gs.pieces = [p.clone() for p in self.pieces]
        gs.current_side = self.current_side
        gs.turn_number = self.turn_number
        gs.phase = self.phase
        gs.winner = self.winner
        gs.sujiang_active = dict(self.sujiang_active)
        gs.pending_luexi_move = None
        gs.pending_guaizi_reaction = None
        gs.move_history = []
        return gs

    def simulate_move(self, piece_id, move):
        clone = self.deep_clone()
        piece = clone.piece_by_id(piece_id)
        if not piece:
            return None
        # 重新映射引用
        cm = Move(move.col, move.row, move.type, special=move.special)
        if move.captured:
            cm.captured = clone.piece_by_id(move.captured.id)
        if move.captured_multi:
            cm.captured_multi = [clone.piece_by_id(cp.id) for cp in move.captured_multi if clone.piece_by_id(cp.id)]
        if move.destroyed:
            cm.destroyed = [clone.piece_by_id(dp.id) for dp in move.destroyed if clone.piece_by_id(dp.id)]
        if move.via and move.via.get('captured'):
            cm.via = dict(move.via)
            cm.via['captured'] = clone.piece_by_id(move.via['captured'].id)

        result = clone.execute_move(piece, cm)
        if not result:
            return None
        if clone.pending_luexi_move:
            clone.skip_luexi_move()
        if clone.pending_guaizi_reaction:
            clone.execute_guaizi_reaction(True)
        return clone
