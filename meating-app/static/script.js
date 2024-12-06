document.addEventListener("DOMContentLoaded", () => {
    // Gestione selezione blocchi extra
    const extraCards = document.querySelectorAll(".extra-card");
    extraCards.forEach(card => {
        card.addEventListener("click", () => {
            const input = card.querySelector(".extra-input");
            if (input.type === "radio") {
                extraCards.forEach(c => c.classList.remove("selected"));
                card.classList.add("selected");
            } else if (input.type === "checkbox") {
                card.classList.toggle("selected");
            }
            input.checked = !input.checked;
        });
    });

    // Validazione form
    const form = document.querySelector("form");
    form.addEventListener("submit", (event) => {
        const quantities = Array.from(form.querySelectorAll("input[type='number']"));
        const total = quantities.reduce((sum, input) => sum + (parseInt(input.value) || 0), 0);

        if (total === 0) {
            event.preventDefault();
            alert("Devi selezionare almeno un piatto o un extra!");
        }
    });
});