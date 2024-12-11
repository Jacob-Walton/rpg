local combat_utils = require("combat_utils")
local core_utils = require("core_utils")

return CreateCommand({
    name = "fireball",
    description = "Cast a fireball at a target",
    usage = "fireball <target>",
    category = "Combat",
    execute = function(args, state)
        local target = core_utils.parseArgs(args)
        if not combat_utils.isValidTarget(target) then
            game:Log("Cast fireball at what?")
            return
        end

        -- Cast fireball effects
        game:Log("You begin casting a fireball...")
        
        game:ExecuteCommand("attack", target)
        
        game:Log("The target burns!")
    end
})
