from django.shortcuts import render, HttpResponse
from django.contrib import messages
from .forms import UserRegistrationForm
from .models import UserRegistrationModel, TokenCountModel, TransactionModel
from django.conf import settings
from datetime import datetime, timedelta
from jose import JWTError, jwt
import socket
import subprocess
import os

# ================= JWT CONFIG =================
SECRET_KEY = "ce9941882f6e044f9809bcee90a2992b4d9d9c21235ab7c537ad56517050f26b"
ALGORITHM = "HS256"


# ================= GET IP =================
def get_ipv4_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return f"Error: {e}"


# ================= TOKEN =================
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ================= REGISTER =================
def UserRegisterActions(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            loginId = form.cleaned_data['loginid']

            TokenCountModel.objects.create(loginid=loginId, count=0)
            form.save()

            # Capture face using external script (optional)
            from .utility import Model_tested
            import subprocess
            import os
            from django.conf import settings

            script_path = os.path.join(settings.BASE_DIR, 'users', 'utility', 'Model_tested.py')

            subprocess.run(
                ["python", script_path, "capture", loginId]
            )

            messages.success(request, 'Registered Successfully')
            return render(request, 'UserRegistrations.html', {'form': UserRegistrationForm()})
        else:
            messages.error(request, 'Email or Mobile Already Exists')
    else:
        form = UserRegistrationForm()

    return render(request, 'UserRegistrations.html', {'form': form})


# ================= LOGIN =================
def UserLoginCheck(request):
    if request.method == "POST":
        loginid = request.POST.get('loginid')
        pswd = request.POST.get('pswd')

        try:
            user = UserRegistrationModel.objects.get(loginid=loginid, password=pswd)

            if user.status == "activated":
                request.session['id'] = user.id
                request.session['loggeduser'] = user.name
                request.session['loginid'] = loginid
                request.session['email'] = user.email

                token = create_access_token({'loginid': loginid})
                request.session['token'] = token

                return render(request, 'users/UserHomePage.html', {'ip': get_ipv4_address()})
            else:
                messages.error(request, 'Account not activated')
        except:
            messages.error(request, 'Invalid login credentials')

    return render(request, 'UserLogin.html')


# ================= HOME =================
def UserHome(request):
    return render(request, 'users/UserHomePage.html', {'ip': get_ipv4_address()})


# ================= TRANSACTION =================
def user_transaction(request):
    if request.method == 'POST':

        sender_id = request.POST.get('sender_id')
        recipient_id = request.POST.get('recipient_id')
        amount = float(request.POST.get('amount'))
        remarks = request.POST.get('remarks')

        # 🔥 Face recognition with sender_id
        try:
            script_path = os.path.join(settings.BASE_DIR, 'users', 'utility', 'Model_tested.py')

            result = subprocess.run(
                ["python", script_path, sender_id],
                capture_output=True,
                text=True
            )

            response = result.stdout.strip().lower().split("\n")[-1]

        except Exception as e:
            print("Subprocess Error:", e)
            response = "failed"

        # ================= SUCCESS =================
        if response == "success":

            from .utility import Model_tested

            otp = Model_tested.generate_otp()
            print("Generated OTP:", otp)   # ✅ DEBUG

            encrypted_otp = Model_tested.encrypt(otp)
            decrypted_otp = Model_tested.decrypt(encrypted_otp)

            request.session['sender_id'] = sender_id
            request.session['recipient_id'] = recipient_id
            request.session['amount'] = amount
            request.session['remarks'] = remarks
            request.session['decrypted_otp'] = decrypted_otp

            return render(request, 'users/otpCheck.html', {
                'otp': decrypted_otp   # ✅ TEMP SHOW
            })

        else:
            return render(request, 'users/faceNotMatch.html',
                          {'msg': "Transaction failed: Face not matched"})

    else:
        loginid = request.session.get('loginid')

        from django.db.models import Q
        users = UserRegistrationModel.objects.filter(~Q(loginid=loginid))

        return render(request, 'users/send_money_form.html',
                      {'loginid': loginid, 'users': users})

# ================= OTP VERIFY =================
def userOtpVerify(request):

    entered_otp = request.POST.get('otpBrw')

    sender_id = request.session.get('sender_id')
    recipient_id = request.session.get('recipient_id')
    amount = request.session.get('amount')
    remarks = request.session.get('remarks')
    decrypted_otp = request.session.get('decrypted_otp')

    if entered_otp == decrypted_otp:
        import uuid
        transaction_id = str(uuid.uuid4())

        TransactionModel.objects.create(
            sender_id=sender_id,
            recipient_id=recipient_id,
            amount=amount,
            remarks=remarks,
            otp=decrypted_otp,
            transaction_id=transaction_id
        )

        from django.db.models import Q
        users = UserRegistrationModel.objects.filter(~Q(loginid=sender_id))

        return render(request, 'users/send_money_form.html',
                      {'loginid': sender_id,
                       'users': users,
                       'msg': f"Transaction Successful. ID: {transaction_id}"})

    else:
        from django.db.models import Q
        users = UserRegistrationModel.objects.filter(~Q(loginid=sender_id))

        return render(request, 'users/send_money_form.html',
                      {'loginid': sender_id,
                       'users': users,
                       'msg': "Transaction failed: Wrong OTP"})


# ================= HISTORY =================
def viewHistory(request):
    login_id = request.session.get('loginid')
    data = TransactionModel.objects.filter(recipient_id=login_id)

    return render(request, 'users/viewHistory.html', {'data': data})