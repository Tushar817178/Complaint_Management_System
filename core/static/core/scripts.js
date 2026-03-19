(function () {
    const alerts = document.querySelectorAll('.alert');
    setTimeout(() => {
        alerts.forEach((alert) => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        });
    }, 4000);
})();

(function () {
    const toggle = document.getElementById('themeToggle');
    if (!toggle) {
        return;
    }
    const current = localStorage.getItem('theme') || 'light';
    document.documentElement.dataset.theme = current;

    toggle.addEventListener('click', () => {
        const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.dataset.theme = next;
        localStorage.setItem('theme', next);
    });
})();
