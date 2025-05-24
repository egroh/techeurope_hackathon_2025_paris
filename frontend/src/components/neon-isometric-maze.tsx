"use client"

import type React from "react"
import { useEffect, useRef, useCallback } from "react"

const NeonIsometricMaze: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>(1)

  const drawMaze = useCallback((ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, time: number) => {
    const cellSize = Math.min(canvas.width, canvas.height) / 10
    const gridWidth = Math.ceil(canvas.width / cellSize) * 2
    const gridHeight = Math.ceil(canvas.height / (cellSize * 0.5)) * 2
    const centerX = canvas.width / 2
    const centerY = canvas.height / 2

    for (let row = -gridHeight; row < gridHeight; row++) {
      for (let col = -gridWidth; col < gridWidth; col++) {
        const x = centerX + ((col - row) * cellSize) / 2
        const y = centerY + ((col + row) * cellSize) / 4
        const distance = Math.sqrt(col * col + row * row)
        const maxDistance = Math.sqrt(gridWidth * gridWidth + gridHeight * gridHeight)
        const intensity = 1 - distance / maxDistance
        const height = cellSize * intensity * Math.abs(Math.sin(distance * 0.5 + time))

        // Draw the isometric cube face
        ctx.beginPath()
        ctx.moveTo(x, y - height)
        ctx.lineTo(x + cellSize / 2, y - cellSize / 2 - height)
        ctx.lineTo(x + cellSize, y - height)
        ctx.lineTo(x + cellSize, y)
        ctx.lineTo(x + cellSize / 2, y + cellSize / 2)
        ctx.lineTo(x, y)
        ctx.closePath()

        // Create gradient fill
        const gradient = ctx.createLinearGradient(x, y - height, x + cellSize, y)
        gradient.addColorStop(0, "rgba(0,255,255,0.8)")
        gradient.addColorStop(1, "rgba(255,0,255,0.8)")
        ctx.fillStyle = gradient
        ctx.fill()

        // Add stroke
        ctx.strokeStyle = "rgba(255,255,0,0.5)"
        ctx.lineWidth = 1
        ctx.stroke()

        // Draw vertical edges
        ctx.beginPath()
        ctx.moveTo(x, y)
        ctx.lineTo(x, y - height)
        ctx.moveTo(x + cellSize, y)
        ctx.lineTo(x + cellSize, y - height)
        ctx.moveTo(x + cellSize / 2, y + cellSize / 2)
        ctx.lineTo(x + cellSize / 2, y - cellSize / 2 - height)
        ctx.strokeStyle = "rgba(255,255,255,0.3)"
        ctx.lineWidth = 1
        ctx.stroke()
      }
    }
  }, [])

  const animate = useCallback(
    (ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement) => {
      let time = 0

      const frame = () => {
        try {
          // Clear with fade effect
          ctx.fillStyle = "rgba(0,0,0,0.1)"
          ctx.fillRect(0, 0, canvas.width, canvas.height)

          // Draw the maze
          drawMaze(ctx, canvas, time)

          time += 0.0025
          animationRef.current = requestAnimationFrame(frame)
        } catch (error) {
          console.error("Animation error:", error)
        }
      }

      frame()
    },
    [drawMaze],
  )

  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) {
      console.error("Failed to get 2D context")
      return
    }

    // Initial setup
    resizeCanvas()

    // Start animation
    animate(ctx, canvas)

    // Handle resize
    window.addEventListener("resize", resizeCanvas)

    return () => {
      window.removeEventListener("resize", resizeCanvas)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [animate, resizeCanvas])

  return <canvas ref={canvasRef} className="block w-full h-full" style={{ display: "block" }} />
}

export default NeonIsometricMaze
