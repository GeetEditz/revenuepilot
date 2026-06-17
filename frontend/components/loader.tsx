"use client";

import React from "react";

export function Loader() {
  return (
    <div className="fixed inset-0 w-screen h-screen z-[9999] flex items-center justify-center bg-black/45 backdrop-blur-md transition-all duration-300">
      <style>{`
        .custom-loader {
          --cell-size: 52px;
          --cell-spacing: 1px;
          --cells: 3;
          --total-size: calc(var(--cells) * (var(--cell-size) + 2 * var(--cell-spacing)));
          display: flex;
          flex-wrap: wrap;
          width: var(--total-size);
          height: var(--total-size);
        }

        .custom-cell {
          flex: 0 0 var(--cell-size);
          margin: var(--cell-spacing);
          background-color: transparent;
          box-sizing: border-box;
          border-radius: 4px;
          animation: 1.5s ripple ease infinite;
        }

        .custom-cell.d-1 {
          animation-delay: 100ms;
        }

        .custom-cell.d-2 {
          animation-delay: 200ms;
        }

        .custom-cell.d-3 {
          animation-delay: 300ms;
        }

        .custom-cell.d-4 {
          animation-delay: 400ms;
        }

        .custom-cell:nth-child(1) {
          --cell-color: #00FF87;
        }

        .custom-cell:nth-child(2) {
          --cell-color: #0CFD95;
        }

        .custom-cell:nth-child(3) {
          --cell-color: #17FBA2;
        }

        .custom-cell:nth-child(4) {
          --cell-color: #23F9B2;
        }

        .custom-cell:nth-child(5) {
          --cell-color: #30F7C3;
        }

        .custom-cell:nth-child(6) {
          --cell-color: #3DF5D4;
        }

        .custom-cell:nth-child(7) {
          --cell-color: #45F4DE;
        }

        .custom-cell:nth-child(8) {
          --cell-color: #53F1F0;
        }

        .custom-cell:nth-child(9) {
          --cell-color: #60EFFF;
        }

        @keyframes ripple {
          0% {
            background-color: transparent;
          }

          30% {
            background-color: var(--cell-color);
          }

          60% {
            background-color: transparent;
          }

          100% {
            background-color: transparent;
          }
        }
      `}</style>
      <div className="custom-loader">
        <div className="custom-cell d-0" />
        <div className="custom-cell d-1" />
        <div className="custom-cell d-2" />
        <div className="custom-cell d-1" />
        <div className="custom-cell d-2" />
        <div className="custom-cell d-2" />
        <div className="custom-cell d-3" />
        <div className="custom-cell d-3" />
        <div className="custom-cell d-4" />
      </div>
    </div>
  );
}

export default Loader;
