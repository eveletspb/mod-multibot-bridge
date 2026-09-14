#include "MaterialMailBatchService.h"

#include "AiObjectContext.h"
#include "Bag.h"
#include "Creature.h"
#include "DatabaseEnv.h"
#include "GameObject.h"
#include "Group.h"
#include "GroupReference.h"
#include "Item.h"
#include "Mail.h"
#include "Player.h"
#include "PlayerbotAI.h"
#include "PlayerbotAIConfig.h"
#include "Playerbots.h"
#include "RandomPlayerbotMgr.h"
#include "RBAC.h"
#include "ScriptMgr.h"
#include "SharedDefines.h"
#include "Value.h"
#include "World.h"
#include "WorldSession.h"

#include <algorithm>
#include <set>
#include <sstream>
#include <utility>

namespace MultiBotBridge
{
namespace
{
uint32 constexpr kMaxBatchBots = 40;
uint32 constexpr kMaxBatchMails = 40;
uint32 constexpr kMaxBatchAttachments = 480;
uint32 constexpr kPostagePerAttachment = 30;
uint32 constexpr kMaxMailboxCountBeforeSend = 100;

char const* const kMailSubject = "Materials from your bots";

struct MaterialAttachmentRef
{
    ObjectGuid guid;
    uint8 bag = 0;
    uint8 slot = 0;
    uint32 itemId = 0;
    uint32 count = 0;
};

struct BotMaterialMailPlan
{
    Player* bot = nullptr;
    ObjectGuid mailboxGuid;
    std::string subject;
    std::string body;
    std::vector<MaterialAttachmentRef> attachments;
    uint32 postage = 0;
    uint32 deliveryDelay = 0;
};

void AddSkipped(MaterialMailBatchResult& result, Player* bot, std::string reason)
{
    MaterialMailSkippedBot skipped;
    skipped.name = bot ? bot->GetName() : "Unknown";
    skipped.reason = std::move(reason);
    result.skipped.push_back(std::move(skipped));
    result.skippedBots = static_cast<uint32>(result.skipped.size());
}

bool IsMaterial(ItemTemplate const* itemTemplate)
{
    if (!itemTemplate || itemTemplate->Quality == ITEM_QUALITY_POOR)
        return false;

    if (itemTemplate->FoodType == PET_DIET_RAW_FISH)
        return true;

    if (itemTemplate->Class == ITEM_CLASS_REAGENT)
        return true;

    if (itemTemplate->Class != ITEM_CLASS_TRADE_GOODS)
        return false;

    switch (itemTemplate->SubClass)
    {
        case ITEM_SUBCLASS_EXPLOSIVES:
        case ITEM_SUBCLASS_CLOTH:
        case ITEM_SUBCLASS_LEATHER:
        case ITEM_SUBCLASS_METAL_STONE:
        case ITEM_SUBCLASS_MEAT:
        case ITEM_SUBCLASS_HERB:
        case ITEM_SUBCLASS_ELEMENTAL:
        case ITEM_SUBCLASS_ENCHANTING:
        case ITEM_SUBCLASS_MATERIAL:
            return true;
        default:
            return false;
    }
}

std::string BuildMailBody(Player* requester, Player* bot)
{
    std::ostringstream body;
    body << "Hello, " << requester->GetName() << ",\n\n"
         << "Here are the materials collected for you.\n\n"
         << "Thanks,\n" << bot->GetName();
    return body.str();
}

ObjectGuid FindInteractableMailbox(Player* bot, PlayerbotAI* botAI)
{
    if (!bot || !botAI || !bot->GetSession() || !botAI->GetAiObjectContext())
        return ObjectGuid::Empty;

    AiObjectContext* const context = botAI->GetAiObjectContext();
    GuidVector const gameObjects = *context->GetValue<GuidVector>("nearest game objects");
    for (ObjectGuid const guid : gameObjects)
    {
        GameObject* const gameObject = botAI->GetGameObject(guid);
        if (gameObject && gameObject->GetGoType() == GAMEOBJECT_TYPE_MAILBOX &&
            bot->GetSession()->CanOpenMailBox(guid))
        {
            return guid;
        }
    }

    GuidVector const npcs = *context->GetValue<GuidVector>("nearest npcs");
    for (ObjectGuid const guid : npcs)
    {
        Unit* const unit = botAI->GetUnit(guid);
        if (unit && unit->HasNpcFlag(UNIT_NPC_FLAG_MAILBOX) && bot->GetSession()->CanOpenMailBox(guid))
            return guid;
    }

    return ObjectGuid::Empty;
}

bool CanMailItem(
    Player* requester,
    Player* bot,
    ObjectGuid mailboxGuid,
    Item* item,
    std::string& subject,
    std::string& body,
    bool runScriptHook)
{
    if (!requester || !bot || !item || item->GetOwnerGUID() != bot->GetGUID())
        return false;

    ItemTemplate const* const itemTemplate = item->GetTemplate();
    if (!IsMaterial(itemTemplate) || item->IsNotEmptyBag() || !item->CanBeTraded(true))
        return false;

    uint32 const senderAccount = bot->GetSession()->GetAccountId();
    uint32 const receiverAccount = requester->GetSession()->GetAccountId();
    if (item->IsBoundAccountWide() && item->IsSoulBound() && senderAccount != receiverAccount)
        return false;

    if (itemTemplate->HasFlag(ITEM_FLAG_CONJURED) || item->GetUInt32Value(ITEM_FIELD_DURATION))
        return false;

    return !runScriptHook || sScriptMgr->OnPlayerCanSendMail(
        bot, requester->GetGUID(), mailboxGuid, subject, body, 0, 0, item);
}

void AppendMaterial(
    Player* requester,
    Player* bot,
    ObjectGuid mailboxGuid,
    uint8 bag,
    uint8 slot,
    Item* item,
    std::string& subject,
    std::string& body,
    std::vector<MaterialAttachmentRef>& attachments)
{
    if (!CanMailItem(requester, bot, mailboxGuid, item, subject, body, true))
        return;

    MaterialAttachmentRef attachment;
    attachment.guid = item->GetGUID();
    attachment.bag = bag;
    attachment.slot = slot;
    attachment.itemId = item->GetEntry();
    attachment.count = item->GetCount();
    attachments.push_back(attachment);
}

std::vector<MaterialAttachmentRef> CollectMaterials(
    Player* requester,
    Player* bot,
    ObjectGuid mailboxGuid,
    std::string& subject,
    std::string& body)
{
    std::vector<MaterialAttachmentRef> attachments;
    subject = kMailSubject;
    body = BuildMailBody(requester, bot);

    for (uint8 slot = INVENTORY_SLOT_ITEM_START; slot < INVENTORY_SLOT_ITEM_END; ++slot)
    {
        AppendMaterial(
            requester, bot, mailboxGuid, INVENTORY_SLOT_BAG_0, slot,
            bot->GetItemByPos(INVENTORY_SLOT_BAG_0, slot), subject, body, attachments);
    }

    for (uint8 bagSlot = INVENTORY_SLOT_BAG_START; bagSlot < INVENTORY_SLOT_BAG_END; ++bagSlot)
    {
        Bag* const bag = bot->GetBagByPos(bagSlot);
        if (!bag)
            continue;

        for (uint32 slot = 0; slot < bag->GetBagSize(); ++slot)
        {
            AppendMaterial(
                requester, bot, mailboxGuid, bagSlot, static_cast<uint8>(slot),
                bag->GetItemByPos(static_cast<uint8>(slot)), subject, body, attachments);
        }
    }

    return attachments;
}

bool IsCrossFactionMailBlocked(Player* requester, Player* bot)
{
    WorldSession* const botSession = bot ? bot->GetSession() : nullptr;
    WorldSession* const requesterSession = requester ? requester->GetSession() : nullptr;
    if (!botSession || !requesterSession)
        return true;

    return botSession->GetAccountId() != requesterSession->GetAccountId() &&
        bot->GetTeamId() != requester->GetTeamId() &&
        !botSession->HasPermission(rbac::RBAC_PERM_TWO_SIDE_INTERACTION_MAIL);
}

std::string GetBotEligibilityFailure(Player* requester, Player* bot, PlayerbotAI* botAI)
{
    if (!bot || !bot->GetSession() || !bot->IsInWorld() || bot->IsDuringRemoveFromWorld() ||
        bot->GetSession()->isLogingOut())
    {
        return "BOT_UNAVAILABLE";
    }

    if (!botAI || !botAI->GetSecurity() ||
        !botAI->GetSecurity()->CheckLevelFor(PLAYERBOT_SECURITY_ALLOW_ALL, true, requester))
    {
        return "FORBIDDEN";
    }

    if (sRandomPlayerbotMgr.IsRandomBot(bot))
        return "RANDOM_BOT";

    if (sRandomPlayerbotMgr.IsAddclassBot(bot))
        return "ADDCLASS_BOT";

    if (!bot->IsAlive())
        return "BOT_DEAD";

    if (bot->IsInCombat())
        return "BOT_IN_COMBAT";

    if (bot->GetTradeData() || bot->IsBeingTeleported())
        return "BOT_BUSY";

    if (sWorld->getBoolConfig(CONFIG_TRIAL_RESTRICTION_MAIL) && bot->GetSession()->IsTrialAccount())
        return "FORBIDDEN";

    if (bot->GetLevel() < sWorld->getIntConfig(CONFIG_MAIL_LEVEL_REQ))
        return "FORBIDDEN";

    if (IsCrossFactionMailBlocked(requester, bot))
        return "CROSS_FACTION_MAIL";

    return "";
}

bool ValidatePlan(Player* requester, std::vector<BotMaterialMailPlan> const& plans)
{
    Group* const group = requester ? requester->GetGroup() : nullptr;
    if (!requester || !requester->GetSession() || !requester->IsInWorld() || !group)
        return false;

    for (BotMaterialMailPlan const& plan : plans)
    {
        Player* const bot = plan.bot;
        PlayerbotAI* const botAI = bot ? sPlayerbotsMgr.GetPlayerbotAI(bot) : nullptr;
        if (!bot || bot->GetGroup() != group || !GetBotEligibilityFailure(requester, bot, botAI).empty() ||
            !bot->GetSession()->CanOpenMailBox(plan.mailboxGuid) || bot->GetMoney() < plan.postage)
        {
            return false;
        }

        std::string subject = plan.subject;
        std::string body = plan.body;
        for (MaterialAttachmentRef const& attachment : plan.attachments)
        {
            Item* const item = bot->GetItemByPos(attachment.bag, attachment.slot);
            if (!item || item->GetGUID() != attachment.guid || item->GetEntry() != attachment.itemId ||
                item->GetCount() != attachment.count ||
                !CanMailItem(requester, bot, plan.mailboxGuid, item, subject, body, false))
            {
                return false;
            }
        }
    }

    return true;
}

void ExecutePlans(
    Player* requester,
    std::vector<BotMaterialMailPlan> const& plans,
    MaterialMailBatchResult& result)
{
    CharacterDatabaseTransaction transaction = CharacterDatabase.BeginTransaction();

    for (BotMaterialMailPlan const& plan : plans)
    {
        Player* const bot = plan.bot;
        bot->ModifyMoney(-static_cast<int32>(plan.postage));
        bot->UpdateAchievementCriteria(ACHIEVEMENT_CRITERIA_TYPE_GOLD_SPENT_FOR_MAIL, plan.postage);

        for (std::size_t start = 0; start < plan.attachments.size(); start += MAX_MAIL_ITEMS)
        {
            MailDraft draft(plan.subject, plan.body);
            std::size_t const end = std::min(start + static_cast<std::size_t>(MAX_MAIL_ITEMS), plan.attachments.size());

            for (std::size_t index = start; index < end; ++index)
            {
                MaterialAttachmentRef const& attachment = plan.attachments[index];
                Item* const item = bot->GetItemByPos(attachment.bag, attachment.slot);

                item->SetNotRefundable(bot);
                bot->MoveItemFromInventory(attachment.bag, attachment.slot, true);
                item->DeleteFromInventoryDB(transaction);
                if (item->GetState() == ITEM_UNCHANGED)
                    item->FSetState(ITEM_CHANGED);
                item->SetOwnerGUID(requester->GetGUID());
                item->SaveToDB(transaction);
                draft.AddItem(item);
            }

            draft.SendMailTo(
                transaction,
                MailReceiver(requester),
                MailSender(bot),
                MAIL_CHECK_MASK_HAS_BODY,
                plan.deliveryDelay);
        }

        bot->SaveInventoryAndGoldToDB(transaction);
        ++result.sentBots;
    }

    CharacterDatabase.CommitTransaction(transaction);
}
}

MaterialMailBatchResult ExecuteMaterialMailBatch(Player* requester, std::vector<Player*> const& visibleBots)
{
    MaterialMailBatchResult result;
    if (!requester || !requester->GetSession() || !requester->IsInWorld())
    {
        result.reason = "BAD_REQUEST";
        return result;
    }

    if (!sPlayerbotAIConfig.botSendMailEnabled)
    {
        result.reason = "DISABLED";
        return result;
    }

    Group* const group = requester->GetGroup();
    if (!group)
    {
        result.reason = "NO_GROUP";
        return result;
    }

    result.scope = group->isRaidGroup() ? "RAID" : "PARTY";

    uint32 const currentMailCount = requester->GetMailSize();
    if (currentMailCount > kMaxMailboxCountBeforeSend)
    {
        result.reason = "RECIPIENT_CAPACITY";
        return result;
    }

    uint32 remainingMailSlots = kMaxMailboxCountBeforeSend + 1 - currentMailCount;
    remainingMailSlots = std::min(remainingMailSlots, kMaxBatchMails);
    uint32 remainingAttachments = kMaxBatchAttachments;
    bool limited = false;

    std::set<ObjectGuid> visibleGuids;
    for (Player* const bot : visibleBots)
        if (bot)
            visibleGuids.insert(bot->GetGUID());

    std::vector<BotMaterialMailPlan> plans;
    for (GroupReference* reference = group->GetFirstMember(); reference && result.matchedBots < kMaxBatchBots;
         reference = reference->next())
    {
        Player* const bot = reference->GetSource();
        if (!bot || bot == requester || visibleGuids.find(bot->GetGUID()) == visibleGuids.end())
            continue;

        PlayerbotAI* const botAI = sPlayerbotsMgr.GetPlayerbotAI(bot);
        if (!botAI)
            continue;

        ++result.matchedBots;
        std::string const eligibilityFailure = GetBotEligibilityFailure(requester, bot, botAI);
        if (!eligibilityFailure.empty())
        {
            AddSkipped(result, bot, eligibilityFailure);
            continue;
        }

        ObjectGuid const mailboxGuid = FindInteractableMailbox(bot, botAI);
        if (!mailboxGuid)
        {
            AddSkipped(result, bot, "NO_MAILBOX");
            continue;
        }

        std::string subject;
        std::string body;
        std::vector<MaterialAttachmentRef> attachments = CollectMaterials(
            requester, bot, mailboxGuid, subject, body);
        if (attachments.empty())
        {
            AddSkipped(result, bot, "NO_MATERIALS");
            continue;
        }

        uint32 const allowedByMailSlots = remainingMailSlots * MAX_MAIL_ITEMS;
        uint32 const selectedCount = std::min<uint32>(
            static_cast<uint32>(attachments.size()),
            std::min(remainingAttachments, allowedByMailSlots));

        if (!selectedCount)
        {
            result.remainingStacks += static_cast<uint32>(attachments.size());
            ++result.truncatedBots;
            limited = true;
            AddSkipped(result, bot, "LIMIT_REACHED");
            continue;
        }

        uint32 const postage = selectedCount * kPostagePerAttachment;
        if (bot->GetMoney() < postage)
        {
            result.remainingStacks += static_cast<uint32>(attachments.size());
            AddSkipped(result, bot, "NOT_ENOUGH_MONEY");
            continue;
        }

        BotMaterialMailPlan plan;
        plan.bot = bot;
        plan.mailboxGuid = mailboxGuid;
        plan.subject = std::move(subject);
        plan.body = std::move(body);
        plan.postage = postage;
        plan.deliveryDelay = bot->GetSession()->GetAccountId() != requester->GetSession()->GetAccountId()
            ? sWorld->getIntConfig(CONFIG_MAIL_DELIVERY_DELAY)
            : 0;
        plan.attachments.assign(attachments.begin(), attachments.begin() + selectedCount);
        plans.push_back(std::move(plan));

        uint32 const mailCount = (selectedCount + MAX_MAIL_ITEMS - 1) / MAX_MAIL_ITEMS;
        remainingMailSlots -= mailCount;
        remainingAttachments -= selectedCount;
        result.sentStacks += selectedCount;
        result.sentMails += mailCount;
        for (uint32 index = 0; index < selectedCount; ++index)
            result.sentItems += attachments[index].count;

        if (selectedCount < attachments.size())
        {
            result.remainingStacks += static_cast<uint32>(attachments.size()) - selectedCount;
            ++result.truncatedBots;
            limited = true;
        }
    }

    if (!result.matchedBots)
    {
        result.reason = "NO_BOTS";
        return result;
    }

    if (plans.empty())
    {
        result.reason = result.skipped.empty() ? "NO_BOTS" : result.skipped.front().reason;
        return result;
    }

    if (!ValidatePlan(requester, plans))
    {
        result.reason = "VALIDATION_FAILED";
        result.sentStacks = 0;
        result.sentItems = 0;
        result.sentMails = 0;
        return result;
    }

    ExecutePlans(requester, plans, result);
    result.status = limited || result.skippedBots ? "PARTIAL" : "OK";
    result.reason = limited ? "TRUNCATED" : "OK";
    return result;
}
}
