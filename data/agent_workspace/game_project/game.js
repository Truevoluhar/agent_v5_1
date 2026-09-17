// Basic setup for canvas and resizing
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}

window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// Placeholder for game logic

// Example: Draw a simple rectangle in center
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#0f0';
    ctx.fillRect(canvas.width/2 - 50, canvas.height/2 - 50, 100, 100);
}

function gameLoop() {
    draw();
    requestAnimationFrame(gameLoop);
}

gameLoop();
