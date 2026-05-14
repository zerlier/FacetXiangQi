"""
命石象棋 - AI 引擎
Alpha-Beta 搜索 + 命石感知评估
"""
import time
import random
from engine import *


class ChessAI:
    BASE_VALUES = {
        PieceType.JIANG: 100000,
        PieceType.CHE: 900,
        PieceType.MA: 400,
        PieceType.PAO: 420,
        PieceType.SHI: 200,
        PieceType.XIANG: 200,
        PieceType.BING: 100,
    }

    POS_BONUS_BING = [
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [5,0,10,0,15,0,10,0,5],
        [5,10,10,10,15,10,10,10,5],
        [15,20,25,35,40,35,25,20,15],
        [20,30,40,50,55,50,40,30,20],
        [25,35,45,60,70,60,45,35,25],
        [30,40,50,65,75,65,50,40,30],
        [35,45,55,70,80,70,55,45,35],
    ]
    POS_BONUS_MA = [
        [-10,5,0,0,0,0,0,5,-10],
        [0,0,10,10,10,10,10,0,0],
        [0,10,20,20,20,20,20,10,0],
        [5,15,25,30,30,30,25,15,5],
        [5,15,25,35,35,35,25,15,5],
        [5,20,30,35,40,35,30,20,5],
        [5,15,30,35,40,35,30,15,5],
        [0,10,25,30,35,30,25,10,0],
        [0,5,15,20,20,20,15,5,0],
        [-10,0,10,10,10,10,10,0,-10],
    ]
    POS_BONUS_CHE = [
        [0,0,0,10,10,10,0,0,0],
        [5,10,10,15,15,15,10,10,5],
        [0,5,10,15,15,15,10,5,0],
        [0,5,10,15,15,15,10,5,0],
        [0,5,10,15,15,15,10,5,0],
        [0,5,10,15,15,15,10,5,0],
        [10,15,20,25,25,25,20,15,10],
        [10,15,20,25,30,25,20,15,10],
        [15,20,25,30,35,30,25,20,15],
        [10,15,20,25,25,25,20,15,10],
    ]
    POS_BONUS_PAO = [
        [0,0,5,5,10,5,5,0,0],
        [0,10,10,15,15,15,10,10,0],
        [5,10,10,15,20,15,10,10,5],
        [0,5,10,10,15,10,10,5,0],
        [0,5,5,5,10,5,5,5,0],
        [0,5,5,5,10,5,5,5,0],
        [0,5,10,10,15,10,10,5,0],
        [0,5,10,15,20,15,10,5,0],
        [5,10,15,20,25,20,15,10,5],
        [0,5,10,15,15,15,10,5,0],
    ]

    POS_TABLES = {
        PieceType.BING: POS_BONUS_BING,
        PieceType.MA: POS_BONUS_MA,
        PieceType.CHE: POS_BONUS_CHE,
        PieceType.PAO: POS_BONUS_PAO,
    }

    def __init__(self, side, difficulty='hard'):
        self.side = side
        self.opponent = Side.BLACK if side == Side.RED else Side.RED
        self.difficulty = difficulty
        self.max_depth = {'easy': 2, 'normal': 3, 'hard': 4}.get(difficulty, 4)
        self.nodes_searched = 0
        self.time_limit = 3.0
        self.start_time = 0

    def evaluate_rune_bonus(self, piece, gs):
        bonus = 0
        r = piece.rune
        if r == Rune.BING_XIANZHEN:
            bonus += 30
        elif r == Rune.BING_WEIBING:
            bonus += 15
        elif r == Rune.BING_FUBING:
            if not piece.has_moved:
                # 计算该方回合数
                if piece.side == Side.RED:
                    side_turns = (gs.turn_number + 1) // 2
                else:
                    side_turns = gs.turn_number // 2
                if side_turns <= 8:
                    bonus += 40  # 同归于尽威慑
        elif r == Rune.PAO_YEZHAN:
            if not piece.yezhan_used:
                bonus += 50
            if piece.move_count < 3:
                bonus -= 20
        elif r == Rune.PAO_ZHONGPAO:
            bonus += 40
            if piece.stun_next_turn:
                bonus -= 30
        elif r == Rune.SHI_JINWEI:
            bonus += 25
        elif r == Rune.SHI_XUNYING:
            bonus += 30
        elif r == Rune.JIANG_DOUJIANG:
            ej = next((p for p in gs.alive_pieces() if p.type == PieceType.JIANG and p.side != piece.side), None)
            if ej and ej.col == piece.col:
                between = gs.pieces_between(piece.col, piece.row, ej.col, ej.row)
                if between and all(b.side == piece.side for b in between):
                    bonus += 500
            bonus += 20
        elif r == Rune.JIANG_SUJIANG:
            bonus += 80
        elif r == Rune.XIANG_DUJUN:
            river = 4 if piece.side == Side.RED else 5
            bonus += 60 if piece.row == river else 15
        elif r == Rune.XIANG_CONGQUAN:
            bonus += 15
        elif r == Rune.MA_QINGQI:
            bonus += 50
        elif r == Rune.MA_YOUMU:
            ally_che = [p for p in gs.alive_pieces(piece.side) if p.type == PieceType.CHE]
            bonus += 40 if not ally_che else -60
        elif r == Rune.MA_GUAIZI:
            bonus += 35
        elif r == Rune.CHE_LUEXI:
            bonus += 30
        elif r == Rune.CHE_HENGXING:
            bonus += 20
        return bonus

    def evaluate(self, gs):
        if gs.phase == 'ended':
            return 999999 if gs.winner == self.side else -999999

        score = 0
        for p in gs.alive_pieces():
            sign = 1 if p.side == self.side else -1
            value = self.BASE_VALUES.get(p.type, 0)
            table = self.POS_TABLES.get(p.type)
            if table:
                r = p.row if p.side == Side.RED else 9 - p.row
                if 0 <= r < 10 and 0 <= p.col < 9:
                    value += table[r][p.col]
            value += self.evaluate_rune_bonus(p, gs)
            if p.type == PieceType.BING and gs.is_crossed_river(p):
                value += 50
            value += len(gs.get_legal_moves(p)) * 3
            score += sign * value

        for side in (self.side, self.opponent):
            jiang = next((p for p in gs.alive_pieces(side) if p.type == PieceType.JIANG), None)
            if jiang:
                sign = 1 if side == self.side else -1
                guards = 0
                for dc, dr in [(0,1),(0,-1),(1,0),(-1,0)]:
                    adj = gs.piece_at(jiang.col + dc, jiang.row + dr)
                    if adj and adj.side == side:
                        guards += 1
                score += sign * guards * 15
                enemy_side = self.opponent if side == self.side else self.side
                enemy_moves = gs.get_all_legal_moves(enemy_side)
                if any(m.col == jiang.col and m.row == jiang.row for _, m in enemy_moves):
                    score -= sign * 200
        return score

    def sort_moves(self, moves):
        def priority(pm):
            p, m = pm
            pri = 0
            if m.captured:
                pri += self.BASE_VALUES.get(m.captured.type, 0)
                pri -= self.BASE_VALUES.get(p.type, 0) / 10
            if m.special:
                pri += 100
                if m.special == 'doujiang':
                    pri += 10000
            if m.captured_multi:
                for cp in m.captured_multi:
                    pri += self.BASE_VALUES.get(cp.type, 0)
            return -pri
        return sorted(moves, key=priority)

    def alpha_beta(self, gs, depth, alpha, beta, maximizing):
        self.nodes_searched += 1
        if time.time() - self.start_time > self.time_limit:
            return self.evaluate(gs)
        if depth == 0 or gs.phase == 'ended':
            return self.evaluate(gs)

        side = self.side if maximizing else self.opponent
        moves = gs.get_all_legal_moves(side)
        if not moves:
            return (-999990 + (self.max_depth - depth)) if maximizing else (999990 - (self.max_depth - depth))

        moves = self.sort_moves(moves)
        max_branch = 15 if depth >= 3 else (20 if depth >= 2 else 30)
        moves = moves[:max_branch]

        if maximizing:
            max_eval = float('-inf')
            for p, m in moves:
                new_gs = gs.simulate_move(p.id, m)
                if not new_gs:
                    continue
                val = self.alpha_beta(new_gs, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, val)
                alpha = max(alpha, val)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for p, m in moves:
                new_gs = gs.simulate_move(p.id, m)
                if not new_gs:
                    continue
                val = self.alpha_beta(new_gs, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, val)
                beta = min(beta, val)
                if beta <= alpha:
                    break
            return min_eval

    def get_best_move(self, gs):
        self.start_time = time.time()
        self.nodes_searched = 0
        moves = self.sort_moves(gs.get_all_legal_moves(self.side))
        if not moves:
            return None
        if len(moves) == 1:
            return moves[0]

        best_move = None
        best_score = float('-inf')

        for depth in range(1, self.max_depth + 1):
            if time.time() - self.start_time > self.time_limit:
                break
            current_best = None
            current_score = float('-inf')
            for p, m in moves:
                if time.time() - self.start_time > self.time_limit:
                    break
                new_gs = gs.simulate_move(p.id, m)
                if not new_gs:
                    continue
                score = self.alpha_beta(new_gs, depth - 1, float('-inf'), float('inf'), False)
                if score > current_score:
                    current_score = score
                    current_best = (p, m)
            if current_best:
                best_move = current_best
                best_score = current_score
            if best_score > 900000:
                break

        elapsed = time.time() - self.start_time
        print(f"AI: depth={self.max_depth}, nodes={self.nodes_searched}, score={best_score}, time={elapsed:.2f}s")
        return best_move

    @staticmethod
    def choose_runes_for_side(gs, side):
        weights_map = {
            Rune.MA_QINGQI: 5, Rune.JIANG_SUJIANG: 4, Rune.BING_FUBING: 4,
            Rune.PAO_ZHONGPAO: 4, Rune.CHE_LUEXI: 3, Rune.SHI_XUNYING: 3,
            Rune.XIANG_DUJUN: 3, Rune.JIANG_DOUJIANG: 3, Rune.MA_GUAIZI: 3,
            Rune.BING_XIANZHEN: 2, Rune.PAO_YEZHAN: 2, Rune.SHI_JINWEI: 2,
            Rune.XIANG_CONGQUAN: 2, Rune.CHE_HENGXING: 2, Rune.BING_WEIBING: 1,
            Rune.MA_YOUMU: 0.5,
        }
        for p in gs.pieces:
            if p.side != side:
                continue
            opts = RUNE_OPTIONS.get(p.type, [])
            useful = [r for r in opts if r != Rune.NONE]
            if not useful:
                continue
            weights = [weights_map.get(r, 1) for r in useful]
            total = sum(weights)
            rand = random.random() * total
            chosen = useful[0]
            for i, r in enumerate(useful):
                rand -= weights[i]
                if rand <= 0:
                    chosen = r
                    break
            p.rune = chosen
