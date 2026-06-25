// Cargar sonido local de gota de agua (mp3)
const clickSound = new Audio('/static/water_drop.mp3');
clickSound.preload = 'auto';
clickSound.volume = 0.85;
clickSound.load();

// Exponer la función globalmente para reproducción manual
window.playClickSound = () => {
    clickSound.currentTime = 0;
    clickSound.play().catch(err => console.log('El audio de clic fue bloqueado o no ha cargado aún:', err));
};

// Función para desbloquear el clickSound en móviles tras la primera interacción
function unlockClickSound() {
    const originalVolume = clickSound.volume;
    clickSound.volume = 0;
    const playPromise = clickSound.play();
    if (playPromise !== undefined) {
        playPromise.then(() => {
            clickSound.pause();
            clickSound.currentTime = 0;
            clickSound.volume = originalVolume;
        }).catch(err => {
            console.log('Error al desbloquear clickSound en móvil:', err);
            clickSound.volume = originalVolume;
        });
    } else {
        clickSound.pause();
        clickSound.currentTime = 0;
        clickSound.volume = originalVolume;
    }
    document.removeEventListener('click', unlockClickSound);
    document.removeEventListener('touchstart', unlockClickSound);
}
document.addEventListener('click', unlockClickSound);
document.addEventListener('touchstart', unlockClickSound);

document.addEventListener('DOMContentLoaded', () => {
    // Escuchar clics globales en la página
    document.addEventListener('click', (e) => {
        // Encontrar si el clic fue en un botón, enlace, opción o elemento interactivo
        const target = e.target.closest('button, .btn, .btn-pill, .btn-submit, .btn-register, .option-btn, .premium-assign-btn, .premium-select, .close-drawer-btn, #sidebar-toggle, #btn-refresh, #btn-show-console, .chest-floating-btn, .role-tab, .sidebar-menu li, .table-list li, a');
        
        if (target) {
            // Reproducir el sonido usando la función global
            window.playClickSound();
            
            // Si el elemento redirige (tiene href o data-href), retrasamos la navegación
            // para permitir escuchar el sonido completo de agua/burbuja
            const href = target.getAttribute('href') || target.getAttribute('data-href');
            const isDownload = target.hasAttribute('download') || (href && (href.startsWith('blob:') || href.startsWith('data:')));
            if (href && href !== '#' && !href.startsWith('javascript:') && !target.getAttribute('target') && !isDownload) {
                e.preventDefault();
                setTimeout(() => {
                    window.location.href = href;
                }, 220); // 220ms de retraso para que se escuche el sonido de agua
            }
        }
    });
});
