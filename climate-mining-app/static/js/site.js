// ClimaTec — interacciones del sitio (menu movil tipo overlay, grafico de
// barras animado del hero). El antiguo desplegable "Etapa 1 ▾" (submenu en
// <ul>) se elimino de aqui: esa navegacion ahora la resuelve la "ruleta"
// (ver ruleta.js), que lee sus datos de los bloques JSON que imprime
// base.html. Este archivo solo sigue encargandose de:
//   1) abrir/cerrar el menu overlay movil (con stagger de entrada, igual
//      que la especificacion de referencia: cada enlace aparece con un
//      pequeno retraso adicional respecto al anterior);
//   2) construir el grafico de barras animado del hero (con datos reales
//      de emisiones, nunca inventados).

document.addEventListener('DOMContentLoaded', () => {
    // ---- Menu movil (overlay) ----------------------------------------
    const toggle = document.querySelector('.menu-toggle');
    const overlay = document.querySelector('.menu-overlay');
    const enlaces = overlay ? overlay.querySelectorAll('.menu-overlay-links a, .menu-overlay-links button') : [];

    function abrirMenu() {
        overlay.classList.add('abierto');
        toggle.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
        enlaces.forEach((a, i) => { a.style.transitionDelay = (100 + i * 50) + 'ms'; });
    }
    function cerrarMenu() {
        overlay.classList.remove('abierto');
        toggle.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
        enlaces.forEach((a) => { a.style.transitionDelay = '0ms'; });
    }
    if (toggle && overlay) {
        toggle.addEventListener('click', () => {
            overlay.classList.contains('abierto') ? cerrarMenu() : abrirMenu();
        });
        const fondo = overlay.querySelector('.menu-overlay-fondo');
        if (fondo) fondo.addEventListener('click', cerrarMenu);
        overlay.querySelectorAll('a').forEach((a) => a.addEventListener('click', cerrarMenu));
    }
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 1024 && overlay && overlay.classList.contains('abierto')) {
            cerrarMenu();
        }
    });

    // ---- Grafico de barras animado (hero) -----------------------------
    // Lee los valores desde data-valores="12,45,30,..." en .bar-chart,
    // dibuja una barra por valor y las hace crecer en cascada. El
    // retraso por barra (1100ms + i*30ms) replica literalmente el
    // timeline de animacion de la especificacion de referencia.
    document.querySelectorAll('.bar-chart[data-valores]').forEach((contenedor) => {
        const valores = contenedor.dataset.valores
            .split(',')
            .map((v) => parseFloat(v.trim()))
            .filter((v) => !Number.isNaN(v));
        if (!valores.length) return;

        const max = Math.max(...valores);
        const barrasEl = contenedor.querySelector('.barras');
        const rejillaEl = contenedor.querySelector('.rejilla');
        if (!barrasEl) return;

        const nProyectadas = parseInt(contenedor.dataset.proyectadas || '0', 10);
        barrasEl.innerHTML = '';
        valores.forEach((valor, i) => {
            const barra = document.createElement('div');
            const alturaPct = max > 0 ? (valor / max) * 100 : 0;
            const esProyectada = i >= valores.length - nProyectadas;
            barra.className = 'barra animate-bar-grow' + (esProyectada ? ' proyectada' : '');
            barra.style.height = alturaPct + '%';
            barra.style.animationDelay = (1100 + i * 30) + 'ms';
            barra.title = valor.toString();
            barrasEl.appendChild(barra);
        });

        if (rejillaEl) {
            rejillaEl.innerHTML = '';
            [0, 1, 2, 3].forEach((i) => {
                const linea = document.createElement('span');
                linea.style.left = (((i + 1) / 4) * 100) + '%';
                rejillaEl.appendChild(linea);
            });
        }
    });
});
