// ClimaTec — interacciones del sitio (menu movil, submenu, marcado de
// enlace activo dentro de "Etapa 1", y utilidades de animacion).
// Sin frameworks, sin IntersectionObserver: las animaciones de entrada
// las dispara el CSS (@keyframes + animation-delay), este script solo
// gestiona interaccion (menu) y arma el grafico de barras del hero.

document.addEventListener('DOMContentLoaded', () => {
    // ---- Menu movil -------------------------------------------------
    const toggle = document.querySelector('.menu-toggle');
    const nav = document.getElementById('nav');
    if (toggle && nav) {
        toggle.addEventListener('click', () => {
            const abierto = nav.classList.toggle('abierto');
            toggle.setAttribute('aria-expanded', String(abierto));
            document.body.style.overflow = abierto ? 'hidden' : '';
        });
    }

    // ---- Desplegable "Etapa 1" (funciona en escritorio y movil) ------
    const grupoBtn = document.querySelector('.nav-grupo-btn');
    const grupo = document.querySelector('.nav-grupo');
    if (grupoBtn && grupo) {
        grupoBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            grupo.classList.toggle('abierto');
            grupoBtn.setAttribute('aria-expanded', String(grupo.classList.contains('abierto')));
        });
        document.addEventListener('click', () => grupo.classList.remove('abierto'));
    }

    // Cierra el menu movil si cambia a tamano de escritorio
    window.addEventListener('resize', () => {
        if (window.innerWidth > 820 && nav && nav.classList.contains('abierto')) {
            nav.classList.remove('abierto');
            toggle && toggle.setAttribute('aria-expanded', 'false');
            document.body.style.overflow = '';
        }
    });

    // ---- Grafico de barras animado (hero) ----------------------------
    // Lee los valores desde data-valores="12,45,30,..." en .bar-chart,
    // dibuja una barra por valor y las hace crecer en cascada, igual que
    // la referencia de diseno (delay escalonado, origen inferior).
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
            barra.style.animationDelay = (300 + i * 22) + 'ms';
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
