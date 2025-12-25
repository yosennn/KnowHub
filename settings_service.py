from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from models import AppSetting

class SettingsService:
    """应用设置服务，用于管理Prompt等可变配置。"""
    SYSTEM_PROMPT_KEY = "system_prompt"
    ANSWER_PROMPT_KEY = "answer_prompt"

    def get_prompt_settings(self, db: Session) -> Dict[str, Optional[str]]:
        system_prompt = self._get_value(db, self.SYSTEM_PROMPT_KEY)
        answer_prompt = self._get_value(db, self.ANSWER_PROMPT_KEY)
        return {
            "system_prompt": system_prompt if isinstance(system_prompt, str) else None,
            "answer_prompt": answer_prompt if isinstance(answer_prompt, str) else None,
        }

    def update_prompt_settings(self, db: Session, system_prompt: Optional[str], answer_prompt: Optional[str]) -> Dict[str, Optional[str]]:
        self._upsert_value(db, self.SYSTEM_PROMPT_KEY, system_prompt)
        self._upsert_value(db, self.ANSWER_PROMPT_KEY, answer_prompt)
        return self.get_prompt_settings(db)

    def _get_value(self, db: Session, key: str) -> Optional[Any]:
        setting = db.query(AppSetting).filter(AppSetting.key == key).first()
        return setting.value if setting else None

    def _upsert_value(self, db: Session, key: str, value: Optional[Any]) -> None:
        setting = db.query(AppSetting).filter(AppSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            setting = AppSetting(key=key, value=value)
            db.add(setting)
        db.commit()
        db.refresh(setting)