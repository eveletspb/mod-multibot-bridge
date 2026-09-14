#ifndef MOD_MULTIBOT_BRIDGE_MATERIAL_MAIL_BATCH_SERVICE_H
#define MOD_MULTIBOT_BRIDGE_MATERIAL_MAIL_BATCH_SERVICE_H

#include "Define.h"

#include <string>
#include <vector>

class Player;

namespace MultiBotBridge
{
struct MaterialMailSkippedBot
{
    std::string name;
    std::string reason;
};

struct MaterialMailBatchResult
{
    std::string scope = "GROUP";
    std::string status = "ERR";
    std::string reason = "INTERNAL_ERROR";
    uint32 matchedBots = 0;
    uint32 sentBots = 0;
    uint32 skippedBots = 0;
    uint32 truncatedBots = 0;
    uint32 sentStacks = 0;
    uint32 remainingStacks = 0;
    uint32 sentItems = 0;
    uint32 sentMails = 0;
    std::vector<MaterialMailSkippedBot> skipped;
};

MaterialMailBatchResult ExecuteMaterialMailBatch(Player* requester, std::vector<Player*> const& visibleBots);
}

#endif
