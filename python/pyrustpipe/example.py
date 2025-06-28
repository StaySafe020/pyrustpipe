from pyrustpipe import Pipeline

@Pipeline
class UserSchema:
    @classmethod
    def user_id(cls):
        cls._pipeline.field(type=int, required=True)

    @classmethod
    def email(cls):
        cls._pipeline.field(type=str, required=True)

schema = UserSchema()._pipeline.to_schema()
print(schema)