from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib import messages
from Account.models import Account,Transactions
from django.http import JsonResponse
import cv2
import numpy as np
import dlib
from keras_facenet import FaceNet
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import os
import stripe
from decimal import Decimal
from django.contrib.auth.decorators import login_required


def home(request):
  return render(request, "home.html")


def user_login(request):
    if request.method=='POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            print(user.first_name)
            return redirect('dashboard')
        else:
            messages.error(request, 'Incorrect username or password')
            return render(request, 'login.html')
    return render(request, 'login.html')


def signup(request):
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        mobile = request.POST['mobile']
        password = request.POST['password']
        password2 = request.POST['password2']

        # Check if passwords match
        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'signup.html')

        # Create a new user
        user = User.objects.create_user(first_name=first_name, last_name=last_name, email=email, username=email, password=password)

        # Create an associated account
        account = Account(user=user, mobile=mobile)
        account.save()

        # Log in the user
        authenticated_user = authenticate(request, username=email, password=password)
        if authenticated_user:
            login(request, authenticated_user)

        # Store data in session
        request.session['user_id'] = user.id
        request.session['mobile'] = mobile

        # Redirect to pinpage
        return redirect('pinpage')

    return render(request, 'signup.html')


def user_logout(request):
    logout(request)
    return redirect('home')


def dashboard(request):
    return render(request, "dashboard.html")

def transaction(request):
    transactions =  Transactions.objects.filter(user_id=request.user.id)
    return render(request, "transaction.html",{'transactions': transactions })

def receive(request):
    return render(request, "receive.html")

def profile(request):
    user_profile = Account.objects.get_or_create(user=request.user)[0]

    if request.method == 'POST':
        # Check if 'profile_image' is in request.FILES to avoid errors
        if 'profile_image' in request.FILES:
            # Delete the old profile image file if it exists
            if user_profile.profile_image:
                default_storage.delete(user_profile.profile_image.name)

            # Save the new uploaded image to user profile
            user_profile.profile_image = request.FILES['profile_image']
            user_profile.save()
            # Call add_user to capture face and update embeddings
            add_user(request)
            # messages.success(request, '✔ Profile updated successfully.' )
            return redirect('profile')

    return render(request, 'profile.html', {'user_profile': user_profile})


# ********************* Face Embeddings Generating & Storing *********************
#Generating Face embeddings & Storing in DB
model = FaceNet()
def get_face_embedding(face_pixels):
  face_pixels = cv2.resize(face_pixels, (160, 160))
  face_pixels = face_pixels / 255.0 # Normalize the face pixels
  samples = np.expand_dims(face_pixels, axis=0)
  #Gettings the embeddings using facenet
  embeddings = model.embeddings(samples)
  return embeddings[0]

def add_user(request):
    user_profile = Account.objects.get_or_create(user=request.user)[0]
    if request.method == 'POST':
        # Check if 'profile_image' is in request.FILES to avoid errors
        if 'profile_image' in request.FILES:
            # Save the new uploaded image to user profile
            user_profile.profile_image = request.FILES['profile_image']
            user_profile.save()

        # Get the image name from the database
        image_name = user_profile.profile_image.name if user_profile.profile_image else 'test.jpg'

        # Construct the dynamic file path
        file_path = f'profile_images/{image_name}'

        # function to Capture an image
        image = cv2.imread(file_path)

        # Check if the image data is not empty
        if image is not None and image.size != 0:
            # Convert the frame to grayscale for Dlib face detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Load the pre-trained face detection model from Dlib
            detector = dlib.get_frontal_face_detector()
            # Detect faces with confidence scores using Dlib
            dets, scores, _ = detector.run(gray, upsample_num_times=1)

            # Check if any face is detected with confidence greater than 0.50
            if dets and scores[0] > 0.3:
                print(f"Confidence Score: {scores[0]}")
                # Take the first detected face
                face = dets[0]
                x, y, width, height = face.left(), face.top(), face.width(), face.height()
                face_pixels = image[y:y+height, x:x+width]

                # Get face embedding
                face_embedding = get_face_embedding(face_pixels)
                # Update the user's face embedding in the database
                user_profile.face_data = face_embedding.tobytes()
                user_profile.save()
                print(face_embedding.tobytes())
                messages.success(request, '✔ Facial Data registered successfully.' )
                return redirect('profile')

            else:
                messages.error(request, '❌ Upload your image with face not covered.❌' )
                print("No face detected with confidence greater than 0.50. Please try again.")

        else:
            print("Error: Unable to read the image.")
            messages.error(request, 'Error: No profile image uploaded.')
            # return redirect('profile')
            return render(request, 'profile.html', {'user_profile': user_profile})
# ********************* Face Embeddings Generating & Storing section ends *********************

# ********************* Facial Verification *********************
# Function to convert binary data to NumPy array
def convert_binary_to_numpy(binary_data):
    return np.frombuffer(binary_data, dtype=np.float32)


def recognize_face(request, image_path, threshold=0.6):
    image = cv2.imread(image_path)
    # Convert the frame to grayscale for Dlib face detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Load the pre-trained face detection model from Dlib
    detector = dlib.get_frontal_face_detector()
    # Detect faces with confidence scores using Dlib
    dets, scores, _ = detector.run(gray, upsample_num_times=1)

    # Check if at least one face is detected with confidence greater than 0.1
    if dets and scores[0] > 0.3:
        print(f"Confidence Score: {scores[0]}")
        # Take the first detected face
        face = dets[0]
        x, y, width, height = face.left(), face.top(), face.width(), face.height()
        face_pixels = image[y:y+height, x:x+width]

        # Get face embedding
        print("Starting face embed...")
        face_embedding = get_face_embedding(face_pixels)

        print("Verifying facial data....")
        # Retrieve known_embeddings from the 'account_account' table
        user_profile = Account.objects.get_or_create(user=request.user)[0]
        known_accounts = Account.objects.exclude(face_data__isnull=True).exclude(face_data=b'').exclude(id=user_profile.id)
        known_embeddings = {str(account.mobile): convert_binary_to_numpy(account.face_data) for account in known_accounts}

        for mobile, known_embedding in known_embeddings.items():
            distance = np.linalg.norm(face_embedding - known_embedding)
            # If the distance is below the threshold, recognize the face
            if distance < threshold:
                print("Verification Success.")
                return f"{mobile}"
            else:
                print("Face not Matched.")
        return "No user found."

    else:
        return "No live face detected"



@csrf_exempt
def process_image(request):
    if request.method == 'POST':
        image_data = request.FILES.get('image_data')
        if image_data:
            print("Step1")
            try:
                # Save the image in the "profile_images/toVerify" folder
                save_path = os.path.join(settings.MEDIA_ROOT, 'toVerify', 'captured_image.jpg')
                print("Step2")
                try:
                    with open(save_path, 'wb') as f:
                        for chunk in image_data.chunks():
                            f.write(chunk)
                except Exception as e:
                    print(f'Error saving image: {str(e)}')
                    return JsonResponse({'result': f'Error saving image: {str(e)}'}, status=500)  # Return an error response
                
                # Perform further processing, e.g., use cv2.imread() on the saved image
                recognition_result = recognize_face(request, image_path='profile_images/toVerify/captured_image.jpg', threshold=0.6)
                print("Step3")
                return JsonResponse({'result': recognition_result})  # Send the result as a string
                
            except Exception as e:
                return JsonResponse({'result': f'Error processing image: {str(e)}'}, status=500)  # Return an error response
        else:
            return JsonResponse({'result': 'No image data received'}, status=400)  # Return a bad request response

    return JsonResponse({'result': 'Invalid request method'}, status=405)  # Return a method not allowed response


# Loading the balance to user's account
stripe.api_key = settings.STRIPE_SECRET_KEY


def loadBalance(request):
    user_profile = Account.objects.get(user=request.user)

    if request.method == 'POST':
        amount = request.POST['amount']

        # Check if the amount is less than 1
        if float(amount) < 1:
            return render(request, 'loadBalance.html', {'error_message': 'Enter amount greater than 1', 'balance': user_profile.balance})

        intent = stripe.PaymentIntent.create(
            amount=int(float(amount) * 100),
            currency='npr',
        )

        load_transaction= Transactions(user=User.objects.get(id=user_profile.id),transaction_type='load',amount=amount,sender='Wallet Load')
        load_transaction.save()
        # Update the user's balance in the database
        user_profile.balance += int(float(amount))
        user_profile.save()


        return render(request, 'loadBalance.html', {'client_secret': intent.client_secret, 'balance': user_profile.balance})
    else:
        return render(request, 'loadBalance.html', {'balance': user_profile.balance})



# Transfer Amount
def transferBalance(request):
    user_profile = Account.objects.get(user=request.user)

    if request.method == 'POST':
        mobile = request.POST['mobile']
        amount = request.POST['amount']

        try:
            # Check if the sender has sufficient balance
            if user_profile.balance < Decimal(amount):
                messages.error(request, 'Insufficient balance.')
                return redirect('transferBalance')

            # Check if the receiver's mobile number exists
            receiver_profile = Account.objects.get(mobile=mobile)

            sender_account = User.objects.get(id=user_profile.id)
            reciever_account= User.objects.get(id=receiver_profile.id)

            reciever_transaction = Transactions(user=reciever_account,transaction_type='deposit',amount=amount,sender=user_profile.mobile) 
            reciever_transaction.save()

            sender_transaction = Transactions(user=sender_account,transaction_type='withdraw',amount=amount,receiver=mobile) 
            sender_transaction.save()
            # Update sender's balance

            user_profile.balance -= Decimal(amount)
            user_profile.save()

            # Update receiver's balance
            receiver_profile.balance += Decimal(amount)
            receiver_profile.save()

            messages.success(request, 'Balance transferred successfully.')
            return redirect('transferBalance')
        except Account.DoesNotExist:
            messages.error(request, 'Receiver not found. Please check the mobile number.')
            return redirect('transferBalance')
    else:
        return render(request, 'transferBalance.html', {'balance': user_profile.balance})        
    

def update(request):
    if request.method=='POST':
        user = request.user

        # Update user details
        user.first_name = request.POST.get('firstName', user.first_name)
        user.last_name = request.POST.get('lastName', user.last_name)
        user.email = request.POST.get('email', user.email)
        # Save the changes to the user
        user.save()

        # Update details in the custom model (assuming 'Account' is your custom model)
        account = Account.objects.get(user=user)
        account.mobile = request.POST.get('mobile', account.mobile)
        account.birthday = request.POST.get('birthday', account.birthday)
        account.gender = request.POST.get('gender', account.gender)
        account.save()

        return redirect('profile')
    return render(request, 'update.html')


@login_required
def pinpage(request):
    user = request.user

    if request.method == 'POST':
        try:
            account = Account.objects.get(user=user)
        except Account.DoesNotExist:
            messages.error(request, 'Account not found')
            return render(request, 'pinpage.html')

        new_pin = request.POST['newPin']
        confirm_pin = request.POST['confirmPin']

        # Check if pins match
        if new_pin != confirm_pin:
            messages.error(request, 'Pins do not match')
            return render(request, 'pinpage.html')

        # If pins match, update the account pin
        account.pin = new_pin
        account.save()
        messages.success(request, 'Pin updated successfully')
        return redirect('dashboard')

    return render(request, 'pinpage.html')


# def check_data_in_database(request):
#     user = Account.objects.get(user=request.user)
#     if request.method == 'POST':
#         # Get form data from the request
#         balance = request.POST.get('balance')
#         pin = request.POST.get('pin')

#         if(user.balance < balance):
#             messages.error(request,'Insufficient balance')
#             return JsonResponse({'error': 'Insufficient balance'}, status=400)
        
#         if(user.pin != pin):
#             messages.error(request,'Invalid pin')
#             return JsonResponse({'error': 'Invalid pin '},status = 400 )
#         # Check data in the database (replace with your logic)
#         # Example: Check if the data exists in a Django model
#         # exists_in_database = Account.objects.filter(balance=field1_value, field2=field2_value).exists()

#         # Send a JSON response
#         response_data = {'transaction': 'complete'}
#         return JsonResponse(response_data)

#     # Handle other HTTP methods if needed
#     return JsonResponse({'error': 'Invalid request method'}, status=400)


def check_data(request):
    user_profile = Account.objects.get(user=request.user)
    if request.method == 'POST':
        amount = request.POST.get('balance')
        pin = request.POST.get('pin')
        mobile = request.POST.get('mobile')
        sender = Account.objects.get(mobile=mobile)
        if sender.pin != pin:
            messages.error(request,'Invalid pin')
            return JsonResponse({'message':'invalid pin'},status=400)
        if sender.balance < Decimal(amount):
            messages.error(request,'Insufficient Balance')
            return JsonResponse({'message':'insufficient balance'},status=400)

        # Check if the receiver's mobile number exists
        sender_account = User.objects.get(id=sender.id)
        reciever_account= User.objects.get(id=user_profile.id)

        reciever_transaction = Transactions(user=reciever_account,transaction_type='deposit',amount=amount,sender=mobile) 
        reciever_transaction.save()

        sender_transaction = Transactions(user=sender_account,transaction_type='withdraw',amount=amount,receiver=user_profile.mobile) 
        sender_transaction.save()
        # Update sender's balance

        user_profile.balance += Decimal(amount)
        user_profile.save()

        # Update receiver's balance
        sender.balance -= Decimal(amount)
        sender.save()

        return JsonResponse({'status':200}) 
    else:
       return JsonResponse({'status':400}) 