document.addEventListener("DOMContentLoaded", () => {
    const themeToggleBtn = document.getElementById("theme-toggle");
    
    // Check if user has a preference saved in localStorage
    const savedTheme = localStorage.getItem("theme");

    // Apply the saved theme immediately
    if (savedTheme === "light") {
        document.body.classList.add("light-mode");
    }

    if (themeToggleBtn) {
        // Render correct icon based on state
        updateToggleIcon();

        themeToggleBtn.addEventListener("click", () => {
            // Toggle class
            document.body.classList.toggle("light-mode");

            // Save preference
            if (document.body.classList.contains("light-mode")) {
                localStorage.setItem("theme", "light");
            } else {
                localStorage.setItem("theme", "dark");
            }
            
            updateToggleIcon();
        });
    }

    function updateToggleIcon() {
        if (document.body.classList.contains("light-mode")) {
            themeToggleBtn.innerHTML = "🌙 Dark";
        } else {
            themeToggleBtn.innerHTML = "☀️ Light";
        }
    }
});
