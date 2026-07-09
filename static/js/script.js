(function() {
    // Immediately remove dark class on load
    if (document.documentElement.classList.contains('dark')) {
        document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', 'light');

    // Observe html attributes to prevent dynamic switches to dark mode
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'class' && document.documentElement.classList.contains('dark')) {
                document.documentElement.classList.remove('dark');
            }
        });
    });
    
    // Start observing
    observer.observe(document.documentElement, { attributes: true });
})();
