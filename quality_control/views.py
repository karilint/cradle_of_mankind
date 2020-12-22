from quality_control.models import FinalAnnotation
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import UpdateView
from scans.models import Scan
from cradle_of_mankind.decorators import remember_last_query_params
from django.template.defaulttags import register
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from zooniverse.models import Classification, Retirement, Workflow
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


@login_required
@remember_last_query_params('specimen-numbers', ['page', 'status'])
def specimen_numbers_list(request):
    query = request.GET.get('query')
    status = request.GET.get('status')
    workflow = Workflow.objects.get(pk=6400)
    retirement_list = Retirement.objects.filter(workflow=workflow)
    if status:
        retirement_list = retirement_list.filter(status=status)
    if query:
        try:
            query = int(query)
            scan = Scan.objects.get(pk=query)
            subject = scan.subject
            retirement_list = retirement_list.filter(subject=subject)
        except:
            pass
    retirement_list = retirement_list.order_by('subject__scan__id')

    page = request.GET.get('page', 1)

    paginator = Paginator(retirement_list, 14)

    try:
        retirements = paginator.page(page)
    except PageNotAnInteger:
        retirements = paginator.page(1)
    except EmptyPage:
        retirements = paginator.page(paginator.num_pages)

    header = ['Pfx', 'AN', 'FN',
              'FN (Pre)', 'Shelf', 'Date', 'Published', 'Type', 'PTO']
    values = dict()
    colors = dict()
    for retirement in retirements:
        values[retirement] = len(retirement.classification_set.all())
        colors[retirement] = []
        tasks = ['T9', 'T1', 'T2', 'T5', 'T8', 'T6', 'T3', 'T7', 'T4']
        for task in tasks:
            classifications = retirement.classification_set.all()
            annotations = []
            for classification in classifications:
                annotations.extend(
                    classification.annotation_set.filter(task=task))
            answer_counts = {}
            for annotation in annotations:
                answer_counts[annotation.value] = answer_counts.get(
                    annotation.value, 0) + 1
            if answer_counts:
                max_count = max(answer_counts.values())
                similarity_score = max_count / len(annotations)
                if similarity_score <= 1/len(annotations):
                    colors[retirement].append('red')
                elif similarity_score < 0.5:
                    colors[retirement].append('orange')
                elif similarity_score < 1:
                    colors[retirement].append('yellow')
                else:
                    colors[retirement].append('green')
            else:
                colors[retirement].append('red')

    query = request.GET.get('query')
    status = request.GET.get('status')
    whole_query = f"?query={query}&status={status}"

    return render(request, 'quality_control/quality_control_list.html',
                  {'page_obj': retirements,
                   'header': header,
                   'values': values,
                   'colors': colors,
                   'status': status,
                   'whole_query': whole_query})


@login_required
def specimen_numbers_check(request, pk):
    workflow = Workflow.objects.get(pk=6400)
    scan = Scan.objects.get(id=pk)
    retirement = scan.subject.retirement_set.filter(workflow=workflow).first()
    tasks = {'T9': 'Pfx', 'T1': 'AN', 'T2': 'FN', 'T5': 'FN (Pre)',
             'T8': 'Shelf', 'T6': 'Date', 'T3': 'Published',
             'T7': 'Type', 'T4': 'PTO'}

    if request.method == 'POST':
        if 'back-btn' in request.POST:
            retirement.status = 'waiting'
            retirement.save()
            return redirect('specimen-numbers')
        retirement.status = 'checked'
        retirement.save()
        for question in tasks.values():
            answer = request.POST.get(question, None)
            if answer:
                final = FinalAnnotation()
                final.scan = scan
                final.retirement = retirement
                final.question = question
                final.answer = answer
                final.save()
        if 'next-btn' in request.POST:
            retirements = Retirement.objects.filter(workflow=workflow)
            retirements = retirements.filter(status='to be checked')
            retirements = retirements.filter(
                subject__scan__id__gt=scan.id).order_by('subject__scan__id')
            next_retirement = retirements.first().subject.scan
            if next_retirement is None:
                return redirect('specimen-numbers')
            return redirect('specimen-numbers-check', pk=next_retirement.id)
        return redirect('specimen-numbers')
    questions = []
    for task, name in tasks.items():
        classifications = retirement.classification_set.all()
        annotations = []
        for classification in classifications:
            annotations.extend(
                classification.annotation_set.filter(task=task))
        answers = {}
        for annotation in annotations:
            answers[annotation.value] = answers.get(
                annotation.value, 0) + 1
        answers = {k: v for k, v in sorted(
            answers.items(), key=lambda item: item[1], reverse=True)}
        if answers:
            max_count = max(answers.values())
            similarity_score = max_count / len(annotations)
            if similarity_score <= 1/len(annotations):
                color = 'red'
            elif similarity_score <= 0.5:
                color = 'orange'
            elif similarity_score < 1:
                color = 'yellow'
            else:
                color = 'green'
        else:
            answers[''] = 1
            color = 'red'
        values = answers.keys()
        iterator = iter(values)
        first_value = next(iterator)
        print(first_value)
        questions.append({name: [answers, color, first_value]})

    return render(request, 'quality_control/quality_control_check.html',
                  {'scan': scan, 'questions': questions})


@ register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
