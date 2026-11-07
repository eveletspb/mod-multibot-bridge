#!/usr/bin/env python3
"""Exercise shipped cleanup policy and batch execution without touching a live inventory."""
from pathlib import Path
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / 'src/MultiBotBridge.cpp').read_text()

def function(signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 0
    for pos in range(opening, len(source)):
        if source[pos] == '{':
            depth += 1
        elif source[pos] == '}':
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise ValueError(signature)

prefix = r'''
#include <array>
#include <cassert>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <sstream>
#include <vector>
using uint8 = uint8_t; using uint32 = uint32_t; using ObjectGuid = uint32;
using ChatMsg = int;
constexpr char kFieldSeparator = '~';
constexpr uint32 kMaxStateBots = 128;
constexpr uint8 INVENTORY_SLOT_BAG_0=255, INVENTORY_SLOT_ITEM_START=23, INVENTORY_SLOT_ITEM_END=39,
 INVENTORY_SLOT_BAG_START=19, INVENTORY_SLOT_BAG_END=23, MAX_QUEST_LOG_SIZE=3;
enum { ITEM_CLASS_ARMOR, ITEM_CLASS_QUEST, ITEM_CLASS_KEY, ITEM_CLASS_PROJECTILE, ITEM_CLASS_REAGENT,
 ITEM_CLASS_MISC, ITEM_CLASS_CONSUMABLE, ITEM_CLASS_TRADE_GOODS, ITEM_SUBCLASS_JUNK=0 };
enum { ITEM_USAGE_NONE, ITEM_USAGE_VENDOR, ITEM_USAGE_AH, ITEM_USAGE_DISENCHANT, ITEM_USAGE_EQUIP,
 ITEM_USAGE_REPLACE, ITEM_USAGE_BROKEN_EQUIP, ITEM_USAGE_QUEST, ITEM_USAGE_SKILL, ITEM_USAGE_USE,
 ITEM_USAGE_GUILD_TASK, ITEM_USAGE_KEEP, ITEM_USAGE_AMMO };
enum { ITEM_QUALITY_LEGENDARY=5, ITEM_FLAG_NO_USER_DESTROY=1, EQUIP_ERR_OK=0,
 SPELL_EFFECT_CREATE_ITEM=24, SPELL_EFFECT_CREATE_ITEM_2=25, UNIT_NPC_FLAG_VENDOR=128,
 CREATURE_FLAG_EXTRA_NO_SELL_VENDOR=1, CMSG_SELL_ITEM=1, CMSG_DESTROYITEM=2 };
struct ItemTemplate {
 uint32 ItemId=1, Class=ITEM_CLASS_TRADE_GOODS, SubClass=0, Quality=1, StartQuest=0, SellPrice=1, MaxCount=0;
 bool protectedFlag=false;
 struct Spell {uint32 SpellId=0;}; std::array<Spell,5> Spells{};
 bool HasFlag(int)const{return protectedFlag;}
};
struct Quest {uint32 src=0; std::array<uint32,4> ItemDrop{}, RequiredItemId{};
 uint32 GetSrcItemId()const{return src;}};
struct ObjectManager {std::map<uint32,Quest> quests;
 Quest const* GetQuestTemplate(uint32 id){auto it=quests.find(id);return it==quests.end()?nullptr:&it->second;}
} objects, *sObjectMgr=&objects;
struct SpellInfo {struct Effect {uint32 Effect=0,ItemType=0;};std::array<Effect,3> Effects{};};
struct SpellManager {std::map<uint32,SpellInfo> spells;
 SpellInfo const* GetSpellInfo(uint32 id){auto it=spells.find(id);return it==spells.end()?nullptr:&it->second;}
} spells, *sSpellMgr=&spells;
struct Item {
 ObjectGuid guid=1,owner=2; uint8 bag=255,slot=23; uint32 count=1; int suffix=-42, usage=ITEM_USAGE_VENDOR;
 bool trade=false, refund=false, bop=false, wrapped=false, nonempty=false;
 ItemTemplate proto;
 ObjectGuid GetGUID()const{return guid;} ObjectGuid GetOwnerGUID()const{return owner;}
 bool IsInTrade()const{return trade;} bool IsRefundable()const{return refund;} bool IsBOPTradable()const{return bop;}
 bool IsWrapped()const{return wrapped;} bool IsNotEmptyBag()const{return nonempty;}
 uint8 GetBagSlot()const{return bag;} uint8 GetSlot()const{return slot;}
 uint32 GetEntry()const{return proto.ItemId;} uint32 GetCount()const{return count;}
 ItemTemplate const* GetTemplate()const{return &proto;} int GetItemRandomPropertyId()const{return suffix;}
};
struct Bag {std::vector<Item*> items; uint32 GetBagSize()const{return items.size();}
 Item* GetItemByPos(uint32 slot){return items[slot];}};
struct Creature {ObjectGuid guid=99;bool noSell=false;
 ObjectGuid GetGUID()const{return guid;} bool HasFlagsExtra(int)const{return noSell;}} vendor;
struct WorldPacket {
 std::vector<uint32> data; WorldPacket(int,int=0){}
 template<class T> WorldPacket& operator<<(T v){data.push_back(v);return *this;}
};
namespace WorldPackets::Item {
struct SellItem {WorldPacket packet; SellItem(WorldPacket&& p):packet(std::move(p)){} void Read(){}};
struct DestroyItem {WorldPacket packet; DestroyItem(WorldPacket&& p):packet(std::move(p)){} void Read(){}};
}
struct Player;
struct Session {Player* bot=nullptr; int sales=0,destroys=0; bool veto=false;
 void HandleSellItemOpcode(WorldPackets::Item::SellItem&);
 void HandleDestroyItemOpcode(WorldPackets::Item::DestroyItem&);
};
struct PlayerbotAI {Player* bot=nullptr;bool context=true,gold=false;
 void* GetAiObjectContext(){return context?this:nullptr;} bool HasCheat(int){return gold;}};
namespace BotCheatMask {constexpr int gold=1;}
struct Player {
 ObjectGuid guid=2,loot=0; std::string name="Bot"; bool available=true,world=true,alive=true,combat=false,
 nearby=true,trade=false,casting=false,interact=true,allowed=true; uint32 money=10;
 Session session{this}; PlayerbotAI ai{this}; std::array<uint32,3> quests{};
 std::map<uint32,Item*> items; Bag* bag=nullptr; bool needsQuest=false,rewarded=false;
 ObjectGuid GetGUID()const{return guid;} ObjectGuid GetLootGUID()const{return loot;}
 bool HasQuestForItem(uint32)const{return needsQuest;} uint32 GetQuestSlotQuestId(uint8 s){return quests[s];}
 bool GetQuestRewardStatus(uint32)const{return rewarded;} int CanUseItem(ItemTemplate const*)const{return 0;}
 Item* GetItemByGuid(ObjectGuid g){auto it=items.find(g);return it==items.end()?nullptr:it->second;}
 Item* GetItemByPos(uint8 b,uint32 s){for(auto [_,i]:items)if(i->bag==b&&i->slot==s)return i;return nullptr;}
 Bag* GetBagByPos(uint8 b){return b==19?bag:nullptr;}
 Session* GetSession(){return available?&session:nullptr;} bool IsInWorld(){return world;} bool IsAlive(){return alive;}
 bool IsInCombat(){return combat;} bool IsWithinDistInMap(Player* p,float d){assert(d==30);return p->nearby;}
 void* GetTradeData(){return trade?this:nullptr;} bool IsNonMeleeSpellCast(bool){return casting;}
 Creature* GetNPCIfCanInteractWith(ObjectGuid,int){return interact?&vendor:nullptr;}
 uint32 GetMoney(){return money;} void SetMoney(uint32 v){money=v;} std::string GetName(){return name;}
};
void Session::HandleSellItemOpcode(WorldPackets::Item::SellItem& p){++sales;if(!veto){bot->items.erase(p.packet.data[1]);bot->money+=5;}}
void Session::HandleDestroyItemOpcode(WorldPackets::Item::DestroyItem& p){++destroys;
 auto* i=bot->GetItemByPos(p.packet.data[0],p.packet.data[1]);assert(i);bot->items.erase(i->guid);}
PlayerbotAI* GetBotAI(Player* p){return &p->ai;}
bool CanControlBridgeBot(Player*,Player* p){return p->allowed;}
Creature* FindNearbyInteractiveVendor(Player* p){return p->interact?&vendor:nullptr;}
struct ItemUsageValue {
 PlayerbotAI* ai; std::string qualifier; explicit ItemUsageValue(PlayerbotAI* v):ai(v){}
 void Qualify(std::string s){qualifier=s;} int Calculate(){
  assert(qualifier.find(',')!=std::string::npos);auto entry=std::stoul(qualifier);
  for(auto [_,i]:ai->bot->items)if(i->proto.ItemId==entry){
   assert(qualifier==std::to_string(entry)+","+std::to_string(i->suffix));return i->usage;
  }return ITEM_USAGE_NONE;
 }
};
std::vector<Player*> visibleBots;
auto GetBridgeVisibleBots(Player*){return visibleBots;}
bool rate=true,heavy=true,fresh=true;
bool ConsumeItemActionRateLimit(Player*){return rate;}
bool ConsumeSelfBotHeavyActionRateLimit(Player*){return heavy;}
bool RegisterItemActionToken(Player*,std::string const&){return fresh;}
std::string UrlEncodeField(std::string const& s){return s;}
std::vector<std::pair<std::string,std::string>> packets;
bool SendStateAddonPacket(Player*,ChatMsg,std::string op,std::string payload){packets.push_back({op,payload});return true;}
#define LOG_INFO(...) (void)0
'''
checks = r'''
int main(){
 Player owner; owner.guid=1;
 Player bot; Item oldGear; bot.items[1]=&oldGear;
 assert(IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear));
 for(int usage:{ITEM_USAGE_EQUIP,ITEM_USAGE_REPLACE,ITEM_USAGE_BROKEN_EQUIP,ITEM_USAGE_QUEST,
 ITEM_USAGE_SKILL,ITEM_USAGE_USE,ITEM_USAGE_GUILD_TASK,ITEM_USAGE_KEEP,ITEM_USAGE_AMMO}){
  oldGear.usage=usage;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear));
 }
 for(int usage:{ITEM_USAGE_NONE,ITEM_USAGE_VENDOR,ITEM_USAGE_AH,ITEM_USAGE_DISENCHANT}){
  oldGear.usage=usage;assert(IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear));
 }
 oldGear.slot=15;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear));
 oldGear.slot=40;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear));oldGear.slot=23;
 for(bool* flag:{&oldGear.trade,&oldGear.refund,&oldGear.bop,&oldGear.wrapped,&oldGear.nonempty,&oldGear.proto.protectedFlag}){
  *flag=true;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear));*flag=false;
 }
 for(auto cls:{ITEM_CLASS_KEY,ITEM_CLASS_PROJECTILE,ITEM_CLASS_REAGENT}){
  oldGear.proto.Class=cls;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear));
 }
 oldGear.proto.Class=ITEM_CLASS_CONSUMABLE;oldGear.proto.MaxCount=1;
 assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear));oldGear.proto.MaxCount=0;
 oldGear.proto.Class=ITEM_CLASS_QUEST;oldGear.proto.SellPrice=0;oldGear.usage=ITEM_USAGE_NONE;
 assert(IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear)); // old quest leftover
 bot.quests[0]=50; objects.quests[50].RequiredItemId[0]=1;
 assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear)); // including exact/completed requirement counts
 objects.quests[50].RequiredItemId[0]=2;oldGear.proto.Spells[0].SpellId=10;
 spells.spells[10].Effects[0]={SPELL_EFFECT_CREATE_ITEM,2};
 assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear));
 spells.spells.clear();objects.quests[50].src=1;
 assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear));objects.quests[50].src=0;
 objects.quests[50].ItemDrop[0]=1;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear));
 objects.quests.clear();bot.quests[0]=0;
 Item sell=oldGear, keep=oldGear, extra=oldGear;
 oldGear.guid=1;sell.guid=2;sell.slot=24;sell.proto.ItemId=2;sell.proto.SellPrice=1;sell.usage=ITEM_USAGE_AH;
 keep.guid=3;keep.slot=25;keep.proto.ItemId=3;keep.usage=ITEM_USAGE_EQUIP;
 extra.guid=4;extra.bag=19;extra.slot=0;extra.proto.ItemId=4;extra.proto.SellPrice=1;
 Bag bag;bag.items={&extra};bot.bag=&bag;
 bot.items={{1,&oldGear},{2,&sell},{3,&keep},{4,&extra}};
 uint32 sold=0,destroyed=0,failed=0;bot.ai.gold=true;
 CleanupBridgeBagItems(&owner,&bot,&vendor,sold,destroyed,failed);
 assert(sold==2&&destroyed==1&&failed==0&&bot.items.size()==1&&bot.money==10);
 bot.bag=nullptr;bot.items={{2,&sell}};bot.session.veto=true;sold=destroyed=failed=0;
 CleanupBridgeBagItems(&owner,&bot,&vendor,sold,destroyed,failed);
 assert(sold==0&&destroyed==0&&failed==1&&bot.items.size()==1); // no destruction after veto
 bot.session.veto=false;
 Player far, forbidden, fighting, noVendor;
 far.nearby=false;forbidden.allowed=false;fighting.combat=true;noVendor.interact=false;
 visibleBots={&bot,&far,&forbidden,&fighting,&noVendor};
 packets.clear();RunInventoryCleanupCommand(&owner,0,"token");
 assert(packets.back().first=="CLEANUP_END"&&packets.back().second=="token~PARTIAL~PARTIAL~1~4~1~0~0");
 assert(bot.items.empty()&&forbidden.session.sales==0);
 bot.items={{2,&sell}};owner.combat=true;packets.clear();RunInventoryCleanupCommand(&owner,0,"combat");
 assert(bot.items.size()==1&&packets.back().second=="combat~ERR~IN_COMBAT~0~0~0~0~0");owner.combat=false;
 heavy=false;RunInventoryCleanupCommand(&owner,0,"rate");assert(bot.items.size()==1);heavy=true;
 fresh=false;RunInventoryCleanupCommand(&owner,0,"duplicate");assert(bot.items.size()==1);fresh=true;
 visibleBots.assign(129,&bot);RunInventoryCleanupCommand(&owner,0,"limit");
 assert(bot.items.size()==1&&packets.back().second=="limit~ERR~TOO_MANY_BOTS~0~0~0~0~0");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / 'cleanup.cpp'
    signatures = ['bool IsBridgeCleanupQuestItem(', 'bool IsBridgeCleanupCandidate(',
                  'void CleanupBridgeBagItems(', 'void RunInventoryCleanupCommand(']
    path.write_text(prefix + '\n'.join(function(s) for s in signatures) + checks)
    binary = Path(tmp) / 'cleanup'
    subprocess.run(['c++', '-std=c++20', '-fsanitize=address,undefined', '-g', str(path), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print('Inventory cleanup: current/old quests, useful items, bag scope, native sale/destroy, failures and batch gates passed')
