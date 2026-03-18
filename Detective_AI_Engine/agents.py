import os
import json
import re
import streamlit as st
from groq import Groq
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Background(BaseModel):
    setting: str
    atmosphere: str
    time_period: str
    location_name: str
    weather: str
    theme_name: str # 隨機生成的主題名稱

class MysteryLogic(BaseModel):
    title: str
    victim_name: str
    cause_of_death: str
    time_of_death: str
    motive_category: str
    murder_weapon: str
    key_clue: str
    killer_index: int
    full_story: str # 案件背景故事
    truth_reveal_story: str # 真相全貌（包含作案過程、動機與證據連結）

class DialogueOption(BaseModel):
    label: str  # The text for the button (e.g., "詢問事發當時的行蹤")
    response: str # What the character says back

class Character(BaseModel):
    name: str
    role: str
    personality: str
    relation_to_victim: str
    suspicion_reason: str # 為什麼這個人會被列為嫌疑人的具體事由（根據故事背景）
    initial_alibi: str
    secret_motive: str
    is_killer: bool
    initial_questions: List[str] # 針對 suspicion_reason 設計的初始詢問

class DetectiveEngine:
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if api_key else None
        self.model_name = model_name

    def set_api_key(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def _call_ai(self, prompt: str, schema: BaseModel):
        if not self.client:
            raise ValueError("尚未設定 Groq API 金鑰。")

        is_small_model = "8b" in self.model_name.lower() or "gemma" in self.model_name.lower()
        json_schema = json.dumps(schema.model_json_schema())
        system_msg = f"你是一位大師級的說故事者與神秘小說作家。你必須嚴格遵守以下 JSON 結構輸出：{json_schema}。輸出的內容必須使用繁體中文 (Traditional Chinese)。請直接輸出 JSON 字串，不要包含 ```json 等 Markdown 格式。"

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                model=self.model_name,
                temperature=0.7,
                stream=False,
                response_format={"type": "json_object"}
            )
            response_text = chat_completion.choices[0].message.content
            if not response_text:
                raise ValueError("AI 回傳內容為空。")

            # 強效 JSON 提取邏輯：尋找第一個 { 與最後一個 } 之間的內容
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            data = json.loads(response_text.strip(), strict=False)
            
            # 處理 AI 有時會過度熱心將結果包裝在類名下的情況
            # 例如返回 {"Background": {...}} 而不是 {...}
            if schema.__name__ in data and len(data) == 1:
                data = data[schema.__name__]
            elif "data" in data and len(data) == 1:
                data = data["data"]
                
            return data
        except Exception as e:
            if "rate_limit_exceeded" in str(e).lower():
                st.error("🚨 Groq API 流量已達上限！請嘗試更換側面欄的模型，或稍後再試。")
            else:
                st.error(f"❌ AI 生成失敗: {str(e)}")
            st.stop()

    def generate_background(self, theme=None):
        theme_prompt = f"主題：{theme}" if theme else "請隨機發想一個橫跨古今中外、真實或虛構的獨特案件背景（不限時代、不限地點、不限題材）。"
        prompt = f"扮演世界觀建模代理人。{theme_prompt}。請創建一個細節極其豐富且具備深厚氛圍感的場景描述。請務必使用繁體中文描述。"
        data = self._call_ai(prompt, Background)
        return Background(**data)

    def generate_mystery(self, background: Background, count=4):
        # 根據模型調整字數限制
        is_small = "8b" in self.model_name.lower() or "gemma" in self.model_name.lower()
        word_count = 300 if is_small else 600
        
        prompt = f"""扮演案件邏輯代理人。根據場景撰寫報案卷宗。
        場景：{background.setting} | 地點：{background.location_name} | 主題：{background.theme_name}
        
        請提供：
        1. 案件基本資訊。
        2. **案件開頭故事 (full_story)**：請撰寫一段約 {word_count} 字的故事。
           - 必須描述現場，且停格在偵查開始前。
           - 必須帶入 {count} 名嫌疑人的異常行為。
           - **🚨 嚴格禁令**：絕對不可提及抓到兇手，不可出現現代科技。
        3. **真相還原 (truth_reveal_story)**
           - **🚨 劇情要求**：兇手的動機必須具有「反轉」或「深層心理」元素（例如：悲劇性的誤會、扭曲的信仰、為了保護他人的意外等）。絕對禁止使用老套的動機，如「爭奪遺產」、「單純的見財起意」或「簡單的情殺」！這會讓玩家一下子就猜到。
        4. **兇手編號 (killer_index)**：請務必輸出一個「整數」，範圍是 0 到 {count-1}。
        所有內容請使用繁體中文。"""
        data = self._call_ai(prompt, MysteryLogic)
        return MysteryLogic(**data)

    def generate_characters(self, background: Background, mystery: MysteryLogic, count=4):
        prompt = f"""扮演角色代理人。為此案件【嚴格創建恰好 {count} 名】嫌疑人，他們的名字和設定必須與【案件真相】完全相符。
        
        故事背景：{mystery.full_story}
        線索與死因：{mystery.cause_of_death} | 關鍵證據：{mystery.key_clue}
        
        【🚨 最重要的案件真相】：{mystery.truth_reveal_story}
        
        【🚨 真兇索引編號】：第 {mystery.killer_index} 位嫌疑人（從 0 開始算起）。
        
        請你根據【案件真相】中提到的人物，來建立這 {count} 個角色的詳細資料：
        1. 你輸出的第 {mystery.killer_index} 個角色，其名字與身分必須對應到【案件真相】裡那位真正的殺手！而且 `is_killer` 必須設為 true。
        2. 其他 {count-1} 個角色，必須對應到真相故事中提到的其他角色（或者是符合背景的無辜嫌疑人），他們的 `is_killer` 必須設為 false。
        3. 每位角色的動機和性格必須與他們在【真相】裡的行為一致，設定要有層次感。
        4. **嫌疑事由 (suspicion_reason)**：根據故事與真相，解釋為什麼警方會懷疑他。
        5. **初始詢問 (initial_questions)**：提供 2 個偵探對他進行第一次偵訊的問題。
           - **🚨 嚴格限制**：這些問題必須「完全基於」上面【故事背景】中已經出現的文字或該角色的公開行為！【絕對不可】無中生有編造一些根本沒出現過的東西（如：沒提到的神秘信件、不存在的遺囑、隱藏的保險箱等老掉牙的推理小說設定）！
        
        所有內容請使用繁體中文。"""
        
        class CharacterList(BaseModel):
            characters: List[Character]
            
        data = self._call_ai(prompt, CharacterList)
        characters = [Character(**c) for c in data['characters']]
        
        # 強制修正 killer_index 以確保與最終生成的陣列索引完全吻合
        for i, char in enumerate(characters):
            if char.is_killer:
                mystery.killer_index = i
                break
                
        return characters

    def get_dynamic_response(self, character: Character, question: str, mystery: MysteryLogic):
        """實時生成嫌疑人的回應與後續追問，必須嚴格遵守案發真相"""
        prompt = f"""扮演偵探遊戲中的嫌疑人。
        你的身分：{character.name} ({character.role})
        性格：{character.personality}
        關係：{character.relation_to_victim}
        你是真兇嗎：{"是，你是殺死死者的真凶！但你必須隱瞞真相，試著為自己開脫，只能在對話中無意間留下極微小的破綻。" if character.is_killer else "不是！你是一個無辜者，但你有著自己的秘密。"}
        
        【上帝視角：案件真相全貌】（僅供故事脈絡參考）：{mystery.truth_reveal_story}
        【核心物證】：{mystery.key_clue}
        
        玩家問你："{question}"
        
        請以角色的口吻給出回應，並根據這個回應提供 2 個合適的【後續追問選項】。
        回應規則（極度重要🚨）：
        1. {"你必須隱瞞自己是兇手的事實，可以假裝不知情或把嫌疑推給別人。" if character.is_killer else "做為無辜者，你【絕對不知道】真正的兇手是誰，也不清楚他們的殺人計畫。你只能回答與你相關的事情！即使你知道真相故事的全貌，你也必須扮演一個不知情的局內人。絕不可直接說出誰是兇手！"}
        2. 你的回應必須符合角色的知識範圍，不可編造不合理的神奇設定。
        3. 回應長度控制在 50~100 字之間，展現戲劇張力。
        4. 【🚨 後續追問選項限制】：這 2 個追問選項必須嚴格扣緊你剛才的「回應內容」或場景中的「核心物證」。絕對禁止憑空捏造出劇本裡沒有的道具（例如：神秘信件、秘密協議、未出現過的人名）！"""
        
        class DynamicInteraction(BaseModel):
            response: str
            next_questions: List[str]
            
        return self._call_ai(prompt, DynamicInteraction)
