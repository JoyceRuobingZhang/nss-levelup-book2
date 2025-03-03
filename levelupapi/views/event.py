"""View module for handling requests about events"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import HttpResponseServerError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import serializers
from levelupapi.models import Game, Event, Gamer
from levelupapi.models.status import Status
from levelupapi.views.game import GameSerializer


class EventView(ViewSet):
    """Level up events"""

    def create(self, request):
        """Handle POST operations for events

        Returns:
            Response -- JSON serialized event instance
        """

        event = Event()
        event.name = request.data["name"]
        event.time = request.data["time"]
        gamer = Gamer.objects.get(user=request.auth.user)
        event.host = gamer
        # event.date = request.data["date"]
        # event.description = request.data["description"]
        # event.organizer = gamer
        game = Game.objects.get(pk=request.data["game_id"])
        event.game = game
        event_status = Status.objects.get(pk=1) #{ "id": 1, "title": "Open for signing up"}
        event.status = event_status

        try:
            event.save()
            serializer = EventSerializer(event, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)  
        
        except ValidationError as ex:
            return Response({"reason": ex.message}, status=status.HTTP_400_BAD_REQUEST) 


    def retrieve(self, request, pk=None):
        """Handle GET requests for single event

        Returns:
            Response -- JSON serialized game instance
        """
        try:
            event = Event.objects.get(pk=pk)
            serializer = EventSerializer(event, context={'request': request})
            return Response(serializer.data)
        
        except Exception as ex:  
        # catch broad/generic server error (eg. got more than one same PK)
            return HttpResponseServerError(ex)


    def update(self, request, pk=None):
        """Handle PUT requests for an event

        Returns:
            Response -- Empty body with 204 status code
        """

        event = Event.objects.get(pk=pk)
        event.name = request.data["name"]
        # event.date = request.data["date"]
        event.time = request.data["time"]
        host = Gamer.objects.get(user=request.auth.user)
        event.host = host
        game = Game.objects.get(pk=request.data["gameId"])
        event.game = game
        status = Status.objects.get(pk=request.data["statusId"]) 
        event.status = status
        
        event.save()

        return Response({}, status=status.HTTP_204_NO_CONTENT)
    

    def destroy(self, request, pk=None):
        """Handle DELETE requests for a single game

        Returns:
            Response -- 200, 404, or 500 status code
        """
        try:
            event = Event.objects.get(pk=pk)
            event.delete()

            return Response({}, status=status.HTTP_204_NO_CONTENT)

        except Event.DoesNotExist as ex:
            return Response({'message': ex.args[0]}, status=status.HTTP_404_NOT_FOUND)

        except Exception as ex:
            return Response({'message': ex.args[0]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def list(self, request):
        """Handle GET requests to events resource
        Returns:
            Response -- JSON serialized list of events
        """
        events = Event.objects.all()
        gamer = Gamer.objects.get(user=request.auth.user)
        
         # Set the `joined` property on every event
        for event in events:
            # Check to see if the gamer is in the attendees list on the event
            event.joined = gamer in event.signed_up_by.all()

        # Support filtering events by game
        game = self.request.query_params.get('gameId', None)
        if game is not None:
            events = events.filter(game__id=game) 
            # ⭕️get events by host: 
            # events = Event.objects.filter(host__user=request.auth.user) 
            # The use of the dunderscore(__) here represents a join operation(foreign-key table / cross table).

        serializer = EventSerializer(
            events, many=True, context={'request': request})
        return Response(serializer.data)    


    # ⭕️⭕️⭕️ Custom Action for the specific url '/signup'
    @action(methods=['post', 'delete'], detail=True)
    def signup(self, request, pk=None): 
        """Managing gamers signing up for events"""
        # Django uses the `Authorization` header to determine
        # which user is making the request to sign up
        gamer = Gamer.objects.get(user=request.auth.user)

        try:
            # Handle the case if the client specifies a game
            # that doesn't exist
            event = Event.objects.get(pk=pk)
            
        except Event.DoesNotExist:
            return Response(
                {'message': 'Event does not exist.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # A gamer wants to sign up for an event
        if request.method == "POST":
            try:
                # Using the attendees field on the event makes it simple to add a gamer to the event
                # .add(gamer) will insert into the join table a new row the gamer_id and the event_id
                event.signed_up_by.add(gamer)
                return Response({}, status=status.HTTP_201_CREATED)
            
            except Exception as ex:
                return Response({'message': ex.args[0]})

        # User wants to leave a previously joined event
        elif request.method == "DELETE":
            try:
                # The many to many relationship has a .remove method that removes the gamer from the attendees list
                # The method deletes the row in the join table that has the gamer_id and event_id
                event.signed_up_by.remove(gamer)
                return Response(None, status=status.HTTP_204_NO_CONTENT)
            
            except Exception as ex:
                return Response({'message': ex.args[0]})
    
    
# User
class EventUserSerializer(serializers.ModelSerializer):
    """JSON serializer for event organizer's related Django user"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

# Gamer
class EventGamerSerializer(serializers.ModelSerializer):
    """JSON serializer for event organizer"""
    user = EventUserSerializer(many=False) # many=False means not an array, just a singular object

    class Meta:
        model = Gamer
        fields = ['user']
        
# Game
class GameSerializer(serializers.ModelSerializer):
    """JSON serializer for games"""
    class Meta:
        model = Game
        fields = ('id', 'name', 'player_limit', 'created_by', 'gametype')
        
# Status
class StatusSerializer(serializers.ModelSerializer):
    """JSON serializer for status"""
    class Meta:
        model = Status
        fields = ('id', 'title')

# Event
class EventSerializer(serializers.ModelSerializer):
    """JSON serializer for events"""
    # Serializer with the dependencies goes at the end
    host = EventGamerSerializer(many=False) # many=False means not an array, just a singular object
    game = GameSerializer(many=False)
    status = StatusSerializer(many=False)

    class Meta:
        model = Event # running Event.objects.all()
        fields = ('id', 'game', 'host',
                'name', 'time', 'status', 'joined')