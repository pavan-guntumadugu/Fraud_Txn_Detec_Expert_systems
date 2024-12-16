from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Forward Chaining for Decision
def forward_chaining(transaction_type, transaction_amount, account_opening_balance, account_holder_location, transaction_location, transactions_last_hour, destination_balance):
    # Derived fields
    new_balance = account_opening_balance - transaction_amount
    new_destination_balance = destination_balance + transaction_amount
    transaction_ratio = (transaction_amount / account_opening_balance) if account_opening_balance > 0 else 0
    balance_difference = account_opening_balance - new_balance

    # Rules
    rules = {
        "large_transaction": transaction_amount > 2500,
        "high_transaction_ratio": transaction_ratio > 0.8,
        "high_balance_difference": balance_difference > 5000,
        "risky_transaction_type": transaction_type in ['CASH_OUT', 'TRANSFER'],
        "location_mismatch": account_holder_location.lower() != transaction_location.lower(),
        "unusual_transaction_frequency": transactions_last_hour > 5,
        "high_value_transaction": transaction_amount > 10,
        "very_high_transaction_ratio": transaction_ratio > 0.99,
        "step_risk": transactions_last_hour > 450,
        "low_amount_low_ratio": transaction_amount <= 0 and transaction_ratio <= 0.1,
        "high_ratio_no_impact": transaction_ratio > 10 and balance_difference <= 500,
        "high_increase_dest_balance": (new_destination_balance - destination_balance) > 5000,
        "low_initial_dest_balance": destination_balance < 100
    }

    # Weights
    weights = {
        "large_transaction": 0.35,
        "high_transaction_ratio": 0.25,
        "high_balance_difference": 0.45,
        "risky_transaction_type": 0.2,
        "location_mismatch": 0.25,
        "unusual_transaction_frequency": 0.2,
        "high_value_transaction": 0.3,
        "very_high_transaction_ratio": 0.35,
        "step_risk": 0.1,
        "low_amount_low_ratio": -0.6,
        "high_ratio_no_impact": -0.55,
        "high_increase_dest_balance": 0.3,
        "low_initial_dest_balance": 0.2
    }

    # Calculate Fraud Score
    fraud_score = sum(weights[rule] for rule, condition in rules.items() if condition)

    # Fraud Decision
    fraud_decision = fraud_score > 0.65

    # Risk Level Categorization
    if fraud_score > 0.8:
        risk_level = "High Risk"
    elif fraud_score > 0.5:
        risk_level = "Medium Risk"
    else:
        risk_level = "Low Risk"

    return {
        "fraud_decision": fraud_decision,
        "fraud_score": round(fraud_score, 2),
        "new_balance": new_balance,
        "transaction_ratio": round(transaction_ratio, 2),
        "balance_difference": balance_difference,
        "new_destination_balance": new_destination_balance,
        "rules": rules,
        "weights": weights,
        "risk_level": risk_level
    }


# Backward Chaining for Explanation
def backward_chaining_with_weightage(decision, rules, weights):
    explanations = []
    not_fraud_reasons = []

    rule_explanations = {
        "large_transaction": {"fraud": "Transaction amount is unusually large.", "not_fraud": "Transaction amount is within normal limits."},
        "high_transaction_ratio": {"fraud": "Transaction ratio is too high.", "not_fraud": "Transaction ratio is within acceptable range."},
        "high_balance_difference": {"fraud": "Large difference in account balance detected.", "not_fraud": "Balance difference is within normal limits."},
        "risky_transaction_type": {"fraud": "Transaction type is risky.", "not_fraud": "Transaction type is not risky."},
        "location_mismatch": {"fraud": "Mismatch between account and transaction locations.", "not_fraud": "Locations match."},
        "unusual_transaction_frequency": {"fraud": "High transaction frequency detected.", "not_fraud": "Transaction frequency is normal."},
        "high_value_transaction": {"fraud": "Transaction is unusually high in value.", "not_fraud": "Transaction value is normal."},
        "very_high_transaction_ratio": {"fraud": "Transaction ratio is critically high.", "not_fraud": "Transaction ratio is safe."},
        "step_risk": {"fraud": "Step-based risk detected.", "not_fraud": "Step-based risk is normal."},
        "low_amount_low_ratio": {"fraud": "Suspicious low transaction amount and ratio.", "not_fraud": "Transaction amount and ratio are normal."},
        "high_ratio_no_impact": {"fraud": "High transaction ratio with no impact.", "not_fraud": "Transaction ratio and impact are balanced."},
        "high_increase_dest_balance": {"fraud": "Significant increase in destination account balance.", "not_fraud": "Destination balance increase is normal."},
        "low_initial_dest_balance": {"fraud": "Destination account had very low initial balance.", "not_fraud": "Destination account balance is sufficient."}
    }

    # Generate explanations based on the decision
    weighted_rules = [(rule, condition, weights[rule]) for rule, condition in rules.items()]
    sorted_rules = sorted(weighted_rules, key=lambda x: x[2], reverse=True)

    if decision:
        explanations = [rule_explanations[rule]["fraud"] for rule, condition, _ in sorted_rules if condition][:3]
    else:
        not_fraud_reasons = [rule_explanations[rule]["not_fraud"] for rule, condition, _ in sorted_rules if not condition][:3]

    return explanations, not_fraud_reasons


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get data from the form
        transaction_type = request.form.get('transactionType')
        transaction_amount = float(request.form.get('transactionAmount'))
        account_opening_balance = float(request.form.get('accountOpeningBalance'))
        account_holder_location = request.form.get('accountHolderLocation')
        transaction_location = request.form.get('transactionLocation')
        transactions_last_hour = int(request.form.get('transactionsLastHour'))
        destination_balance = float(request.form.get('destinationBalance'))

        # Forward chaining to get decision, rules, and weights
        forward_result = forward_chaining(
            transaction_type, transaction_amount, account_opening_balance,
            account_holder_location, transaction_location, transactions_last_hour, destination_balance
        )

        # Backward chaining for explanations with weightage
        fraud_decision = forward_result["fraud_decision"]
        explanations, not_fraud_reasons = backward_chaining_with_weightage(
            fraud_decision, forward_result["rules"], forward_result["weights"]
        )

        # Combine results
        result = {
            "fraud_decision": "Fraud" if fraud_decision else "Not Fraud",
            "fraud_score": forward_result["fraud_score"],
            "new_balance": forward_result["new_balance"],
            "transaction_ratio": forward_result["transaction_ratio"],
            "balance_difference": forward_result["balance_difference"],
            "new_destination_balance": forward_result["new_destination_balance"],
            "risk_level": forward_result["risk_level"],
            "explanations": explanations if fraud_decision else not_fraud_reasons
        }

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    app.run(debug=True)
