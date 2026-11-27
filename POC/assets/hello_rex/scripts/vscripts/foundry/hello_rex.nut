// Gel can fling a sentry off the landing without ever letting it settle into OnTipped.
function CheckField(count, bankStart) {
    for (local i = 1; i <= count; i++) {
        local name = "sentry_" + i;
        local latch = Entities.FindByName(null, name + "_down");
        if (latch == null) continue;
        local turret = Entities.FindByName(null, name);
        if (turret == null || turret.GetOrigin().y < bankStart || turret.GetUpVector().z < 0.35) {
            EntFireByHandle(latch, "Trigger", "", 0, self, self);
        }
    }
}

function FinishTest() {
    // A direct console launch has no Workshop queue or rating dialog.
    if (GetMapName() == "hello_rex") {
        EntFireByHandle(Entities.FindByName(null, "local_end"), "Command",
                        "disconnect", 1.5, GetPlayer(), self);
    } else {
        EntFire("@relay_pti_level_end", "Trigger");
    }
}
