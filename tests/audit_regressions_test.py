#!/usr/bin/env python3
"""Run shipped bridge functions against small Core/Playerbots stubs."""
from pathlib import Path
import subprocess
import tempfile

src = (Path(__file__).resolve().parents[1] / 'src/MultiBotBridge.cpp').read_text()
def fn(signature):
    offset=0
    while True:
        start=src.index(signature,offset); opening=src.index('{',start)
        if ';' not in src[start:opening]: break
        offset=opening+1
    depth=0
    for pos in range(opening,len(src)):
        if src[pos]=='{': depth+=1
        if src[pos]=='}':
            depth-=1
            if not depth: return src[start:pos+1]
prefix=r'''
#include <algorithm>
#include <cstdint>
#include <cmath>
#include <string>
#include <sstream>
#include <vector>
#include <iostream>
#include <cassert>
#include <sstream>
#include <map>
#include <set>
#include <limits>
#include <chrono>
#include <deque>
using uint8=uint8_t; using uint32=uint32_t; using uint64=uint64_t;
enum { INVTYPE_RELIC,INVTYPE_TRINKET,INVTYPE_2HWEAPON,INVTYPE_WEAPONMAINHAND,INVTYPE_WEAPONOFFHAND,INVTYPE_WEAPON,INVTYPE_HOLDABLE,INVTYPE_SHIELD,INVTYPE_RANGED,INVTYPE_THROWN,INVTYPE_RANGEDRIGHT,INVTYPE_HEAD,INVTYPE_CHEST,INVTYPE_ROBE,INVTYPE_LEGS,INVTYPE_SHOULDERS,INVTYPE_WAIST,INVTYPE_FEET,INVTYPE_HANDS,INVTYPE_NECK,INVTYPE_WRISTS,INVTYPE_FINGER,INVTYPE_CLOAK,INVTYPE_BODY };
constexpr uint8 EQUIPMENT_SLOT_START=0,EQUIPMENT_SLOT_END=19,EQUIPMENT_SLOT_BODY=3,EQUIPMENT_SLOT_MAINHAND=15,EQUIPMENT_SLOT_OFFHAND=16,EQUIPMENT_SLOT_RANGED=17,INVENTORY_SLOT_BAG_0=255,CLASS_HUNTER=3;
struct ItemTemplate {uint32 ItemId=123,Quality=4,ItemLevel=200,InventoryType=INVTYPE_2HWEAPON;};
enum EnchantmentSlot { PERM_ENCHANTMENT_SLOT=0, SOCK_ENCHANTMENT_SLOT=2 };
struct Item {ItemTemplate proto;
 uint32 GetEnchantmentId(EnchantmentSlot slot){return slot==PERM_ENCHANTMENT_SLOT ? 3789 : uint32(slot)+100;}
 int32_t GetItemRandomPropertyId(){return -42;} uint32 GetItemSuffixFactor(){return 12345;}
 ItemTemplate const* GetTemplate() {return &proto;}
};
struct Enchantment {uint32 GemID=0;};
struct EnchantStore {Enchantment entry; Enchantment* LookupEntry(uint32 id){entry.GemID=id+40000;return &entry;}} sSpellItemEnchantmentStore;
constexpr int PLAYERBOT_SECURITY_ALLOW_ALL=2;
struct Player;
struct Security {bool allowed=false; bool CheckLevelFor(int,bool,Player*){return allowed;}};
struct PlayerbotAI {Security security; Security* GetSecurity(){return &security;}};
struct Group {};
struct Player {Item weapon; PlayerbotAI ai; Group* group=nullptr;
 uint32 GetLevel(){return 80;} Group* GetGroup(){return group;} void* GetSession(){return this;} Item* GetItemByPos(uint8,uint8 slot){return slot==15?&weapon:nullptr;} int getClass(){return 6;} std::string GetName(){return "Bot";} };
struct InventoryItemMovePositionState {bool present=false; uint64 guidCounter=0; uint32 itemId=0,count=0;};
using ChatMsg=int;
constexpr char kFieldSeparator='~';
std::string Trim(std::string const&s){return s;}
std::string UrlEncodeField(std::string const&s){return s;}

Player bot;
PlayerbotAI* GetBotAI(Player* player){return player ? &player->ai : nullptr;}
constexpr std::size_t kItemActionRateLimit=24;
constexpr std::chrono::milliseconds kItemActionRateWindow(2000);
bool IsValidRequestToken(std::string const& token){return !token.empty();}
int outfitChanges=0, formationChanges=0;
std::string SanitizeOutfitCommandSuffix(std::string const& s){return s;}
std::string UrlDecodeField(std::string const& s){return s;}
std::string ToUpper(std::string const& s){return s;}
std::string ToLower(std::string const& s){return s;}
bool IsAllowedOutfitCommandSuffix(std::string const&){return true;}
bool ApplyBridgeNativeOutfitCommand(Player*,std::string const&,bool){++outfitChanges; return true;}
bool IsAllowedFormationName(std::string const&){return true;}
bool ConsumeGroupOrderRateLimit(Player*){return true;}
bool RegisterGroupOrderToken(Player*,std::string const&){return true;}
bool SendProtocolError(Player*,ChatMsg,std::string const&,std::string const&,std::string const&,std::string const&){return true;}
std::vector<Player*> GetBridgeVisibleBots(Player*,bool){return {&bot};}
bool ApplyNativeFormation(Player*,std::string const&){++formationChanges;return true;}

Player* FindBotByName(Player*,std::string const&){return &bot;}
bool ConsumeCraftRecipeRateLimit(Player*){return true;}
bool RegisterCraftRecipeToken(Player*,std::string const&){return true;}
std::string ValidateProfessionRecipeCraft(Player*,uint32,uint32,uint32,uint32&){return "OK";}
struct SpellInfo{};
struct SpellMgr {SpellInfo spell; SpellInfo const* GetSpellInfo(uint32){return &spell;}} mgr,*sSpellMgr=&mgr;
bool ProfessionRecipeRequiresExactItemTarget(SpellInfo const*){return false;}
int casts=0;
std::string CastProfessionRecipe(Player*,uint32){++casts;return "OK";}
std::map<std::string,std::vector<std::string>> packets;
void SendAddonPacket(Player*,ChatMsg,std::string const& op,std::string const& payload){packets[op].push_back(payload);}
bool SendStateAddonPacket(Player* p,ChatMsg type,std::string const& op,std::string const& payload){
 assert(5+op.size()+payload.size()<=255);SendAddonPacket(p,type,op,payload);return true;
}
uint32 BuildItemLevelScore(Player*){return 200;}
struct PlayerbotsMgr {PlayerbotAI* GetPlayerbotAI(Player* p){return GetBotAI(p);}} sPlayerbotsMgr;
'''
functions = src[src.index('struct ItemActionRateState'):src.index('// MB_TALENT_APPLY_V1_BEGIN')]
functions = fn('bool TryParseUint32Field(') + functions
functions += '\n'.join(fn(signature) for signature in [
    'float GearScoreSlotModifier(', 'uint32 GearScoreForItem(', 'uint32 BuildGearScore(',
    'bool InventoryItemMoveStateMatchesExpected(', 'bool CanControlBridgeBot(',
    'void RunProfessionRecipeCraftCommand(', 'void RunOutfitCommand(', 'void RunFormationCommand(',
    'void SendGearInspectPackets('
])
checks = r'''
int main() {
 Player requester; Group group; requester.group=&group; bot.group=&group;
 assert(BuildGearScore(&bot)==GearScoreForItem(&bot.weapon.proto));
 InventoryItemMovePositionState original{true,111,123,1}, replacement{true,222,123,1}, empty;
 assert(InventoryItemMoveStateMatchesExpected(original,123,1,111));
 assert(!InventoryItemMoveStateMatchesExpected(replacement,123,1,111));
 assert(!InventoryItemMoveStateMatchesExpected(original,123,2,111));
 assert(InventoryItemMoveStateMatchesExpected(empty,0,0,0));
 assert(!InventoryItemMoveStateMatchesExpected(empty,0,0,111));
 RunProfessionRecipeCraftCommand(&requester,0,"Bot","craft","171","123","0");
 RunOutfitCommand(&requester,0,"Bot","outfit","saved RESET","1");
 RunFormationCommand(&requester,0,"GROUP","","formation","near");
 assert(casts==0 && outfitChanges==0 && formationChanges==0);
 bot.ai.security.allowed=true;
 RunProfessionRecipeCraftCommand(&requester,0,"Bot","craft2","171","123","0");
 RunOutfitCommand(&requester,0,"Bot","outfit2","saved UPDATE","1");
 RunFormationCommand(&requester,0,"GROUP","","formation2","near");
 assert(casts==1 && outfitChanges==1 && formationChanges==1);
 SendGearInspectPackets(&requester,0,"Bot","gear-token");
 assert(packets["GEAR_LINK"].size()==1);
 assert(packets["GEAR_LINK"][0]=="Bot~gear-token~15~item:123:3789:40102:40103:40104:0:-42:12345:80");
 assert(ConsumeItemActionRateLimit(&requester));
 assert(RegisterItemActionToken(&requester,"purchase"));
 assert(ConsumeItemActionRateLimit(&requester));
 assert(!RegisterItemActionToken(&requester,"purchase"));
 assert(RegisterItemActionToken(&requester,"purchase2"));
 auto& state=sItemActionRateStates.at(requester.GetName());
 state.recentTokens.front().second-=std::chrono::seconds(11);
 assert(RegisterItemActionToken(&requester,"purchase"));
 for (int i=2;i<24;++i) assert(ConsumeItemActionRateLimit(&requester));
 assert(!ConsumeItemActionRateLimit(&requester));
}
'''
orders_prefix=r'''
#include <algorithm>
#include <cstdint>
#include <cmath>
#include <string>
#include <iostream>
#include <cassert>
#include <sstream>
#include <map>
using uint8=uint8_t;using uint32=uint32_t;
constexpr uint8 NULL_BAG=255,NULL_SLOT=255;
struct ObjectGuid {int value=1; bool operator==(ObjectGuid const&)const=default; explicit operator bool()const{return value;} };
constexpr int BOT_STATE_COMBAT=0,BOT_STATE_NON_COMBAT=1,PLAYERBOT_SECURITY_ALLOW_ALL=2;
struct PositionInfo {bool set=true; void Reset(){set=false;} void Set(float,float,float,uint32){set=true;} };
using PositionMap=std::map<std::string,PositionInfo>;
struct Player;
struct Security {bool CheckLevelFor(int,bool,Player*){return true;}};
struct Value {PositionMap positions;PositionMap& Get(){return positions;} void Reset(){} };
struct Context {Value value;template<class T>Value*GetValue(std::string const&){return &value;}};
struct GuidVector{};
struct PlayerbotAI {Player* master;Security sec;Context context;bool reset=false,passive=true,pullBack=false,pull=false;
 Security*GetSecurity(){return &sec;}Player*GetMaster(){return master;}Context*GetAiObjectContext(){return &context;}
 bool HasStrategy(std::string const& s,int){return s=="pull" ? pull : pullBack;}
 void Reset(){reset=true;}
 void ChangeStrategy(std::string const& s,int){
  if(s=="-passive")passive=false;
  std::istringstream input(s); std::string op;
  while(std::getline(input,op,',')) {
   if(op=="+pull")pull=true; if(op=="-pull")pull=false;
   if(op=="+pull back")pullBack=true; if(op=="-pull back")pullBack=false;
  }
 }
};
struct Player {PlayerbotAI ai{this,{},{},false,true,false,false};uint32 money=10000,count=0;
 uint32 GetMoney(){return money;}uint32 GetItemCount(uint32,bool){return count;}
 float GetReputationPriceDiscount(void*){return 1.0f;}
 void BuyItemFromVendorSlot(ObjectGuid,uint32,uint32,int,uint8,uint8){count+=5;money-=100;}
 float GetPositionX(){return 0;}float GetPositionY(){return 0;}float GetPositionZ(){return 0;}uint32 GetMapId(){return 1;}
 ObjectGuid GetGUID(){return {};} };
PlayerbotAI*GetBotAI(Player*p){return &p->ai;}
struct ItemTemplate{uint32 BuyPrice=100,BuyCount=5;};
struct ObjectMgr{ItemTemplate proto;ItemTemplate const*GetItemTemplate(uint32){return &proto;}}objectMgr,*sObjectMgr=&objectMgr;
struct Creature{ObjectGuid GetGUID()const{return {};}} vendor;
Creature*FindNearbyVendorSellingItem(Player*,uint32,uint32&,uint32&,bool&){return &vendor;}
struct Event {Event(){}Event(char const*,char const*,Player*){}};
bool pullAccepted=false;
struct PullMyTargetAction{PullMyTargetAction(PlayerbotAI*){}bool Execute(Event){return pullAccepted;}};
struct AttackMyTargetAction{AttackMyTargetAction(PlayerbotAI*){}bool Execute(Event){return false;}};
bool VerifyGroupOrderState(Player*,Player*,PlayerbotAI*,std::string const&){return true;}
'''
orders_functions=fn('uint32 BuyMatchingVendorItem(')+'\n'+fn('bool ApplyNativeGroupOrder(Player* requester, Player* bot, std::string const& command)')
orders_checks = r'''
int main() {
 Player p; std::string reason;
 assert(BuyMatchingVendorItem(&p,123,3,reason)==5 && p.money==9900);
 assert(BuyMatchingVendorItem(&p,123,10,reason)==10 && p.money==9700);
 assert(!ApplyNativeGroupOrder(&p,&p,"@tank pull back"));
 assert(!p.ai.reset && p.ai.passive && !p.ai.pullBack && !p.ai.pull);
 assert(p.ai.context.value.positions["stay"].set && p.ai.context.value.positions["return"].set);
 p.ai.pull=true; p.ai.pullBack=true;
 assert(!ApplyNativeGroupOrder(&p,&p,"@tank pull"));
 assert(p.ai.pull && p.ai.pullBack && p.ai.passive);
 pullAccepted=true;
 assert(ApplyNativeGroupOrder(&p,&p,"@tank pull back"));
 assert(p.ai.pull && p.ai.pullBack && !p.ai.passive && !p.ai.reset);
 assert(p.ai.context.value.positions["stay"].set && !p.ai.context.value.positions["return"].set);
}
'''
dispatch_prefix = r'''
constexpr uint32 kMaxBotNameLength=64,kMaxInventoryItemDestroyCount=1000,kMaxInventoryItemMoveCount=1000;
int mutations=0;
bool IsValidCanonicalRawField(std::string const& s,uint32,bool){return !s.empty();}
template<class... Args> void RunInventoryItemDestroyCommand(Args...){++mutations;}
template<class... Args> void RunInventoryItemMoveCommand(Args...){++mutations;}
'''
dispatch = fn('std::string GetSafeErrorToken(')
dispatch += 'bool Dispatch(Player* player, std::vector<std::string> const& fields) { ChatMsg replyType=0; std::string normalized="RUN", requestType=fields.at(0);'
dispatch += fn('if (requestType == "ITEM_DESTROY")')
dispatch += fn('if (requestType == "ITEM_MOVE")')
dispatch += 'return false;}'
dispatch_checks = r'''
int main(){
 Player p;
 std::vector<std::string> destroy={"ITEM_DESTROY","Bot","token","255","23","123","1"};
 Dispatch(&p,destroy); assert(mutations==0);
 destroy.push_back("0"); Dispatch(&p,destroy); assert(mutations==0);
 destroy.back()="4294967296"; Dispatch(&p,destroy); assert(mutations==0);
 destroy.back()="111"; Dispatch(&p,destroy); assert(mutations==1);
 std::vector<std::string> move={"ITEM_MOVE","Bot","token","255","23","123","1","255","24","0","0","111","0"};
 Dispatch(&p,move); assert(mutations==2);
 move.back()="-1"; Dispatch(&p,move); assert(mutations==2);
 move.pop_back(); Dispatch(&p,move); assert(mutations==2);
}
'''
with tempfile.TemporaryDirectory(prefix='multibot-audit-') as directory:
    for name, code in [('contracts', prefix + functions + checks),
                       ('orders', orders_prefix + orders_functions + orders_checks),
                       ('dispatch', prefix + functions + dispatch_prefix + dispatch + dispatch_checks)]:
        cpp = Path(directory) / (name + '.cpp')
        executable = Path(directory) / name
        cpp.write_text(code)
        subprocess.run(['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror', str(cpp), '-o', str(executable)], check=True)
        subprocess.run([str(executable)], check=True)
print('Bridge audit: authorization, GUID identity, replay/rate limits, GS, vendor units and pull rollback passed')
