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

    // ---- Desplegables de nav ("Etapa 1", "Etapa 2") -----------------
    // Cada grupo abre/cierra su propio submenu; al abrir uno se cierran
    // los demas. Funciona en escritorio y movil.
    const grupos = Array.from(document.querySelectorAll('.nav-grupo'));
    grupos.forEach((grupo) => {
        const btn = grupo.querySelector('.nav-grupo-btn');
        if (!btn) return;
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const abierto = grupo.classList.contains('abierto');
            grupos.forEach((g) => {
                g.classList.remove('abierto');
                const b = g.querySelector('.nav-grupo-btn');
                if (b) b.setAttribute('aria-expanded', 'false');
            });
            if (!abierto) {
                grupo.classList.add('abierto');
                btn.setAttribute('aria-expanded', 'true');
            }
        });
    });
    document.addEventListener('click', () => {
        grupos.forEach((g) => {
            g.classList.remove('abierto');
            const b = g.querySelector('.nav-grupo-btn');
            if (b) b.setAttribute('aria-expanded', 'false');
        });
    });

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
