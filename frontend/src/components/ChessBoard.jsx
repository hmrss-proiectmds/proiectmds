import { useState, useMemo } from 'react';
import './ChessBoard.css';

const PIECE_SYMBOLS = {
  wK: '♔', wQ: '♕', wR: '♖', wB: '♗', wN: '♘', wP: '♙',
  bK: '♚', bQ: '♛', bR: '♜', bB: '♝', bN: '♞', bP: '♟',
};

const FILES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
const RANKS = ['8', '7', '6', '5', '4', '3', '2', '1'];

/**
 * Interactive chess board with click-to-move.
 *
 * Props:
 *  - board: 8x8 array (rank8→rank1) of "wP"|"bK"|null
 *  - legalMoves: ["e2e4", ...] UCI strings
 *  - lastMove: {from: "e2", to: "e4"} | null
 *  - isCheck: boolean
 *  - turnSeat: 1|2 (whose turn)
 *  - yourSeat: 1|2 (your color)
 *  - onMove: (uci) => void
 *  - disabled: boolean
 *  - fen: string (for king square detection)
 */
export default function ChessBoard({
  board,
  legalMoves = [],
  lastMove,
  isCheck,
  turnSeat,
  yourSeat,
  onMove,
  disabled = false,
  fen = '',
}) {
  const [selectedSquare, setSelectedSquare] = useState(null);
  const flipped = yourSeat === 2;

  // Build a set of legal destination squares for the selected piece
  const legalFromSelected = useMemo(() => {
    if (!selectedSquare) return new Set();
    return new Set(
      legalMoves
        .filter((m) => m.startsWith(selectedSquare))
        .map((m) => m.slice(2, 4))
    );
  }, [selectedSquare, legalMoves]);

  // Build set of squares that have legal moves (to show clickable pieces)
  const movableSources = useMemo(() => {
    return new Set(legalMoves.map((m) => m.slice(0, 2)));
  }, [legalMoves]);

  // Find king square for check highlight
  const kingInCheck = useMemo(() => {
    if (!isCheck || !board) return null;
    const kingPiece = turnSeat === 1 ? 'wK' : 'bK';
    for (let r = 0; r < 8; r++) {
      for (let f = 0; f < 8; f++) {
        if (board[r][f] === kingPiece) {
          return `${FILES[f]}${RANKS[r]}`;
        }
      }
    }
    return null;
  }, [isCheck, board, turnSeat]);

  const handleSquareClick = (file, rank, squareName, piece) => {
    if (disabled || turnSeat !== yourSeat) return;

    if (selectedSquare) {
      if (legalFromSelected.has(squareName)) {
        // Check for pawn promotion
        let moveUci = selectedSquare + squareName;
        const selectedPiece = getPieceAt(selectedSquare);
        if (
          selectedPiece &&
          (selectedPiece === 'wP' || selectedPiece === 'bP') &&
          (squareName[1] === '8' || squareName[1] === '1')
        ) {
          moveUci += 'q'; // auto-promote to queen
        }
        onMove(moveUci);
        setSelectedSquare(null);
        return;
      }
      // Click on own piece → re-select
      if (piece && isOwnPiece(piece) && movableSources.has(squareName)) {
        setSelectedSquare(squareName);
        return;
      }
      setSelectedSquare(null);
      return;
    }

    // Select a piece
    if (piece && isOwnPiece(piece) && movableSources.has(squareName)) {
      setSelectedSquare(squareName);
    }
  };

  const isOwnPiece = (piece) => {
    if (!piece) return false;
    if (yourSeat === 1) return piece.startsWith('w');
    return piece.startsWith('b');
  };

  const getPieceAt = (squareName) => {
    const f = FILES.indexOf(squareName[0]);
    const r = RANKS.indexOf(squareName[1]);
    if (f < 0 || r < 0 || !board) return null;
    return board[r][f];
  };

  if (!board) return null;

  const renderRows = flipped ? [...Array(8).keys()].reverse() : [...Array(8).keys()];
  const renderCols = flipped ? [...Array(8).keys()].reverse() : [...Array(8).keys()];

  return (
    <div className="chess-board-wrapper">
      <div className="chess-board" id="chess-board">
        {renderRows.map((r) =>
          renderCols.map((f) => {
            const squareName = `${FILES[f]}${RANKS[r]}`;
            const piece = board[r][f];
            const isLight = (r + f) % 2 === 0;
            const isSelected = selectedSquare === squareName;
            const isLegalTarget = legalFromSelected.has(squareName);
            const isLastMoveFrom = lastMove?.from === squareName;
            const isLastMoveTo = lastMove?.to === squareName;
            const isKingCheck = kingInCheck === squareName;
            const isMovable = !disabled && turnSeat === yourSeat && piece && isOwnPiece(piece) && movableSources.has(squareName);

            let className = `chess-square ${isLight ? 'light' : 'dark'}`;
            if (isSelected) className += ' selected';
            if (isLastMoveFrom || isLastMoveTo) className += ' last-move';
            if (isKingCheck) className += ' in-check';
            if (isMovable) className += ' movable';

            return (
              <div
                key={squareName}
                className={className}
                data-square={squareName}
                onClick={() => handleSquareClick(f, r, squareName, piece)}
              >
                {/* Coordinate labels */}
                {f === (flipped ? 7 : 0) && (
                  <span className={`coord-rank ${isLight ? 'coord-dark' : 'coord-light'}`}>
                    {RANKS[r]}
                  </span>
                )}
                {r === (flipped ? 0 : 7) && (
                  <span className={`coord-file ${isLight ? 'coord-dark' : 'coord-light'}`}>
                    {FILES[f]}
                  </span>
                )}

                {/* Legal move dot */}
                {isLegalTarget && !piece && <span className="legal-dot" />}
                {isLegalTarget && piece && <span className="legal-capture" />}

                {/* Piece */}
                {piece && (
                  <span className={`chess-piece ${piece.startsWith('w') ? 'white-piece' : 'black-piece'}`}>
                    {PIECE_SYMBOLS[piece]}
                  </span>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
