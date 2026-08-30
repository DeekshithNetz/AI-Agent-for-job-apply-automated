import requests


BASE_URL = "http://127.0.0.1:8000"


# =========================================================
# START APPLICATION
# =========================================================

url = input(
    "Internship/Application URL: "
).strip()

profile_id = int(
    input(
        "Profile ID: "
    )
)

response = requests.post(
    f"{BASE_URL}/agent/apply",
    params={
        "url": url,
        "profile_id": profile_id
    }
)

result = response.json()

print("\n================================")
print("AGENT RESULT")
print("================================")

print(result)


# =========================================================
# USER INTERVENTION LOOP
# =========================================================

while result.get(
    "status"
) == "waiting_for_user":

    session_id = result[
        "session_id"
    ]

    questions = result[
        "questions"
    ]

    print(
        "\n================================"
    )

    print(
        "AI NEEDS MORE INFORMATION"
    )

    print(
        "================================\n"
    )

    answers = {}

    for question in questions:

        key = question.get(
            "key"
        )

        description = question.get(
            "description",
            key
        )

        field_type = question.get(
            "type",
            "text"
        )

        print(
            f"\nQuestion: {description}"
        )

        # ---------------------------------------------
        # RADIO
        # ---------------------------------------------

        if field_type == "radio":

            options = question.get(
                "options",
                []
            )

            if options:

                print(
                    "Options:"
                )

                for option in options:

                    print(
                        "-",
                        option.get(
                            "label"
                        )
                        or option.get(
                            "value"
                        )
                    )

        answer = input(
            "Your answer: "
        ).strip()

        answers[key] = answer

    # =====================================================
    # SEND ANSWERS
    # =====================================================

    response = requests.post(
        f"{BASE_URL}/agent/answer",
        json={
            "session_id":
                session_id,
            "answers":
                answers
        }
    )

    result = response.json()

    print(
        "\n================================"
    )

    print(
        "AGENT RESULT"
    )

    print(
        "================================"
    )

    print(
        result
    )


print(
    "\nAgent finished."
)