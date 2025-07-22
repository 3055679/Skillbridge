// Global JavaScript that will be loaded on all pages
document.addEventListener("DOMContentLoaded", function () {
  // You can add global event listeners or initialization code here
  console.log("SkillBridge JavaScript loaded");

  // Example: Add click handler for all dropdown items
  document.querySelectorAll(".dropdown-item").forEach((item) => {
    item.addEventListener("click", function () {
      // Handle dropdown item clicks
    });
  });
});
